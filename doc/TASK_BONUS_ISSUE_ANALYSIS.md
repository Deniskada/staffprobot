# Анализ: Корректировка за выполненную задачу не создаётся

**Дата:** 29.10.2025  
**Проблема:** Задача отмечена выполненной в боте, отправлено фото, но корректировка (премия +100₽) не создана  
**Смена:** 307

---

## 🔍 Текущее состояние БД

### Смена 307
```sql
id: 307
user_id: 14
object_id: 9
status: completed
end_time: 2025-10-29 15:37:42 UTC (18:37 MSK)
total_payment: 138.00
```

### Задача (TaskEntryV2)
```sql
id: 3
shift_id: 307
template_id: 6 (Влажная уборка)
employee_id: 14
is_completed: FALSE  ❌ НЕ ПОМЕЧЕНА КАК ВЫПОЛНЕННАЯ!
completed_at: NULL
completion_media: NULL
```

### Корректировки (PayrollAdjustment)
```sql
id: 428 | shift_base | +138.00 | Базовая оплата
id: 429 | late_start | -6.00   | Штраф за опоздание

НЕТ корректировки task_bonus на +100₽ ❌
```

---

## 🎯 Корневая причина

**Задача НЕ была помечена как выполненная в БД!**

**Проблема в логике бота:**
- Пользователь нажал галочку на задаче
- Бот запросил фото (т.к. `requires_media=True`)
- Пользователь отправил фото
- **Обработчик `_handle_received_task_v2_media` НЕ сработал**

---

## 🔍 Хронология событий

```
15:36 UTC (18:36 MSK) - Бот перезапущен ✅
15:37 UTC (18:37 MSK) - Смена 307 закрыта ❌
                        Задача НЕ помечена как выполненная
```

**Вывод:** Смена закрыта сразу после перезапуска бота или даже во время перезапуска!

**Возможные причины:**
1. Бот ещё не загрузился полностью
2. Обработчик фото не зарегистрировался
3. Пользователь закрыл смену НЕ через бот (через веб?)

---

## 🔎 Проверка сценариев

### Сценарий 1: Смена закрыта через веб-интерфейс
**Проверка:**
```sql
SELECT * FROM shifts WHERE id = 307;
-- end_time: 2025-10-29 15:37:42.697018
-- Смена БЫЛА закрыта (есть end_time)
```

**Если закрыта через веб:**
- Задачи в БД не обрабатываются
- Нужна интеграция с веб-роутом закрытия смены

### Сценарий 2: Смена закрыта через бот со СТАРЫМ кодом
**Временная метка:**
- Бот перезапущен: 15:36 UTC
- Смена закрыта: 15:37 UTC (через 1 минуту!)

**Вероятность:** Высокая!  
Бот ещё использовал старый код (до полной загрузки нового)

### Сценарий 3: Обработчик медиа не зарегистрирован
**Проверка регистрации обработчиков:**
```python
# apps/bot/main.py или handlers регистрация
# Должен быть MessageHandler для фото с фильтром TASK_V2_MEDIA
```

---

## 💡 Откуда должна создаться корректировка?

### Вариант A: При отметке задачи в боте (НЕМЕДЛЕННО)
**Где:**
- `apps/bot/handlers_div/shift_handlers.py:_handle_complete_task_v2`
- `apps/bot/handlers_div/shift_handlers.py:_handle_received_task_v2_media`

**Логика:**
```python
# После is_completed = True
# Создать PayrollAdjustment сразу
adjustment = PayrollAdjustment(
    employee_id=entry.employee_id,
    shift_id=entry.shift_id,
    task_entry_v2_id=entry.id,
    adjustment_type="task_bonus",
    amount=template.default_bonus_amount
)
```

**Статус:** ❌ Такого кода НЕТ в обработчиках бота!

### Вариант B: Через Celery (ОТЛОЖЕННО)
**Где:**
- `core/celery/tasks/task_bonuses.py:process_task_bonuses_celery`
- Запускается каждые 10 минут

**Логика:**
```python
# Найти is_completed = True
# Создать PayrollAdjustment
```

**Статус:** ✅ Код ЕСТЬ, но celery worker НЕ запущен на dev!

---

## 🐛 Найденные проблемы

### Проблема 1: Celery worker не запущен на dev ❌
```bash
$ docker compose -f docker-compose.dev.yml ps celery-worker
no such service: celery-worker
```

**Последствие:**
- `process_task_bonuses_celery` не выполняется
- Корректировки за задачи не создаются автоматически

### Проблема 2: Задача не помечена как выполненная ❌
```sql
is_completed: FALSE
completed_at: NULL
completion_media: NULL
```

**Последствие:**
- Даже если запустить celery - корректировка НЕ создастся (is_completed = False)

### Проблема 3: Нет мгновенного создания корректировки в боте ⚠️
**Сейчас:**
- Задача помечается выполненной
- Корректировка создаётся через celery (каждые 10 мин)

**Проблема:** На dev нет celery → корректировки никогда не создадутся!

---

## 💡 Решения

### ✅ Решение 1 (временное для dev): Ручное создание корректировки

```sql
-- Пометить задачу как выполненную (если не помечена)
UPDATE task_entries_v2 
SET is_completed = true,
    completed_at = NOW()
WHERE id = 3;

-- Создать корректировку вручную
INSERT INTO payroll_adjustments (
    shift_id, employee_id, object_id, task_entry_v2_id,
    adjustment_type, amount, description, 
    created_by, is_applied
) VALUES (
    307, 14, 9, 3,
    'task_bonus', 100.00, 'Задача: Влажная уборка',
    1, false
);
```

### ✅ Решение 2 (для прода): Запустить celery worker

**На проде celery должен работать:**
```bash
docker compose -f docker-compose.prod.yml ps
# Должны быть: celery-worker, celery-beat
```

**Celery автоматически создаст корректировки** для всех выполненных задач каждые 10 минут.

### ✅ Решение 3 (архитектурное): Создавать корректировку сразу в боте

**Добавить в `_handle_complete_task_v2` и `_handle_received_task_v2_media`:**
```python
# После entry.is_completed = True и commit
if template.default_bonus_amount:
    # Создать корректировку сразу
    adjustment = PayrollAdjustment(...)
    session.add(adjustment)
    await session.commit()
```

**Плюсы:**
- Мгновенная обратная связь
- Не зависит от celery

**Минусы:**
- Дублирование логики (celery + бот)

---

## 📋 План восстановления для текущей смены 307

**Шаг 1:** Проверить была ли смена закрыта через бот или веб
```bash
docker compose -f docker-compose.dev.yml logs web --since 30m | grep "close.*shift.*307"
```

**Шаг 2:** Вручную создать корректировку (для теста)
```sql
-- См. Решение 1 выше
```

**Шаг 3:** Открыть НОВУЮ смену и протестировать весь flow с актуальным кодом бота

---

## ✅ Для нового теста

**Рекомендации:**
1. Открыть смену 308 на объекте 9 (есть план задач)
2. Отметить задачу выполненной
3. Отправить фото
4. Проверить что `is_completed = TRUE` в БД
5. Вручную вызвать celery задачу `process_completed_tasks_bonuses`
6. Проверить создание корректировки

---

**Статус:** Требуется решение - вручную создать корректировку или протестировать на новой смене?  
**Автор:** AI Assistant


