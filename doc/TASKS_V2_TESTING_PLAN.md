# План тестирования Tasks v2

**Дата:** 29.10.2025  
**Цель:** Проверить полный цикл работы задач v2

---

## ✅ Подготовка завершена

**Контейнеры перезапущены:**
- ✅ web (16:25 UTC)
- ✅ bot (15:36 UTC) 
- ✅ celery_worker (15:56 UTC)
- ✅ celery_beat (15:56 UTC)

**Celery работает:**
- ✅ Worker запущен и зарегистрировал `process_task_bonuses`
- ✅ Beat запущен
- ⚠️ Задача `process-task-bonuses` НЕ в расписании (нужно добавить в BEAT_SCHEDULE)

**БД готова:**
- ✅ Таблицы Tasks v2 созданы
- ✅ Ключи фич обновлены (tasks_v2)
- ✅ Legacy задачи очищены
- ✅ План id=2 создан для объекта 9

---

## 📋 Тестовый сценарий

### Тест 1: Создание и выполнение задачи (полный цикл)

**Шаг 1:** Открыть новую смену
```
Пользователь: techpodru (user_id=14)
Объект: Home Office (object_id=9)
Ожидается: TaskEntryV2 создастся автоматически
```

**Проверка в БД:**
```sql
-- Найти последнюю смену
SELECT id, object_id, status FROM shifts 
WHERE user_id = 14 AND object_id = 9 
ORDER BY id DESC LIMIT 1;

-- Проверить создание задачи
SELECT id, shift_id, template_id, is_completed 
FROM task_entries_v2 
WHERE shift_id = (последняя смена);

-- Ожидается: 1 запись с is_completed = FALSE
```

**Шаг 2:** Проверить отображение задачи в боте
```
Кнопка: "📋 Мои задачи"
Ожидается: Список с задачей "Влажная уборка"
```

**Шаг 3:** Отметить задачу выполненной
```
Действие: Нажать галочку на задаче
Ожидается: Запрос фото (т.к. requires_media = TRUE)
```

**Шаг 4:** Отправить фото
```
Действие: Отправить фото в бот
Ожидается: 
- Фото отправится в Telegram группу объекта
- Задача пометится is_completed = TRUE
- completion_media сохранится
```

**Проверка в БД:**
```sql
SELECT id, is_completed, completed_at, completion_media::text
FROM task_entries_v2 
WHERE shift_id = (текущая смена);

-- Ожидается:
-- is_completed: TRUE ✅
-- completed_at: NOT NULL ✅
-- completion_media: [{...}] ✅
```

**Шаг 5:** Закрыть смену
```
Действие: Закрыть смену через бот
Ожидается: Смена закрыта, создан shift_base
```

**Шаг 6:** Вызвать celery задачу вручную
```bash
docker compose -f docker-compose.dev.yml exec celery_worker \
  celery -A core.celery.celery_app call process_task_bonuses
```

**Шаг 7:** Проверить создание корректировки
```sql
SELECT id, shift_id, employee_id, adjustment_type, amount, description, task_entry_v2_id
FROM payroll_adjustments
WHERE task_entry_v2_id IS NOT NULL
ORDER BY id DESC
LIMIT 3;

-- Ожидается:
-- task_bonus, amount=100.00, description="Задача: Влажная уборка" ✅
```

---

## 🐛 Найденная проблема

**Задача `process-task-bonuses` НЕ в расписании celery beat!**

**В celery_app.py:**
```python
'process-task-bonuses': {
    'task': 'process_task_bonuses',
    'schedule': 600,  # каждые 10 минут
}
```

**Но в логах beat:**
```
НЕТ сообщений "Sending due task process-task-bonuses"
```

**Причина:** Beat использовал старую БД расписания (`/tmp/celerybeat-schedule`)

**Решение:**
```bash
# Удалить старый файл расписания
docker compose -f docker-compose.dev.yml exec celery_beat rm /tmp/celerybeat-schedule

# Перезапустить beat
docker compose -f docker-compose.dev.yml restart celery_beat
```

---

## 🔧 Исправления для автоматической работы

### Исправление 1: Очистка celerybeat-schedule

```bash
docker compose -f docker-compose.dev.yml exec celery_beat rm -f /tmp/celerybeat-schedule
docker compose -f docker-compose.dev.yml restart celery_beat
```

### Проверка после исправления:

```bash
# Через 1-2 минуты проверить логи
docker compose -f docker-compose.dev.yml logs celery_beat --tail 50 | grep "process-task-bonuses"

# Ожидается:
# [TIME] Scheduler: Sending due task process-task-bonuses (process_task_bonuses)
```

---

## ✅ Критерии успешного теста

- [ ] Задача создаётся при открытии смены
- [ ] Задача отображается в боте
- [ ] Задачу можно отметить выполненной
- [ ] При requires_media=TRUE запрашивается фото
- [ ] После отправки фото is_completed = TRUE
- [ ] Celery beat запускает process-task-bonuses каждые 10 мин
- [ ] Celery worker создаёт корректировку для выполненной задачи
- [ ] Корректировка отображается в /owner/payroll/adjustments

---

**Статус:** Требуется исправление celerybeat-schedule и повторный тест  
**Автор:** AI Assistant


