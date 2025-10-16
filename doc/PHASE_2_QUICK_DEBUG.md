# 🔧 БЫСТРАЯ ДИАГНОСТИКА БАГ #4 (Корректировки)

## 📌 ШАГ 1: Проверь статус смены

```sql
-- Какой статус присваивается когда ты закрываешь смену?
SELECT id, status, updated_at, closed_at FROM shifts 
WHERE user_id = (SELECT id FROM users WHERE telegram_id = YOUR_TELEGRAM_ID)
ORDER BY created_at DESC LIMIT 5;

-- Ожидается: status = 'completed' (НЕ 'closed')
-- Если видишь: status = 'closed' → это проблема!
```

## 📌 ШАГ 2: Проверь adjustment_tasks.py логику

Строка 49 в `core/celery/tasks/adjustment_tasks.py`:
```python
Shift.status == 'completed',  # ← Ищет смены со статусом 'completed'
```

**Если смена имеет статус `'closed'`, а не `'completed'` → Celery её не найдёт!**

## 📌 ШАГ 3: Где устанавливается status при закрытии?

Ищи в коде:
```bash
grep -r "status.*=.*closed\|status.*=.*completed" /home/sa/projects/staffprobot/apps/web/services/ /home/sa/projects/staffprobot/apps/bot/ --include="*.py"
```

Должны найтись:
- Где устанавливается `'closed'` 
- Где устанавливается `'completed'`

## 📌 ШАГ 4: Проверь, есть ли пропуск статусов

```python
# В adjustment_tasks.py на строке 49, может быть нужно:
Shift.status.in_(['closed', 'completed']),  # Оба статуса
```

---

## 🚀 БЫСТРЫЙ ФИХ ДЛЯ БАГ #4

Если статус смены `'closed'`, а Celery ищет `'completed'`:

**Вариант 1: Изменить SQL (быстро)**
```python
# В adjustment_tasks.py строка 49
# БЫЛО:
Shift.status == 'completed',

# БУДЕТ:
Shift.status.in_(['closed', 'completed']),
```

**Вариант 2: Изменить статус при закрытии (правильно)**
```python
# Где-то в коде закрывается смена, должно быть:
shift.status = 'completed'  # НЕ 'closed'
```

---

## 🔍 Для БАГ #1, #2, #3

Добавь логирование в код и проверь логи:

**БАГ #1 - Название задачи:**
```python
# В _load_timeslot_tasks() строка 48
logger.info(f"TASK_DEBUG: task_text='{template.task_text}', id={template.id}")
```

**БАГ #2 - ignore_object_tasks:**
```python
# В _collect_shift_tasks() строка 96
logger.info(f"DEBUG_IGNORE: timeslot.ignore_object_tasks={timeslot.ignore_object_tasks if timeslot else None}")
```

**БАГ #3 - Двойная геопозиция:**
```python
# В handle_location() в начале
logger.info(f"LOCATION_DEBUG: latitude={update.message.location.latitude}, user_state={user_state}")
```
