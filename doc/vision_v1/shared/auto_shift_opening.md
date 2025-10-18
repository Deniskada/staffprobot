# Автооткрытие последовательных смен

## Назначение
Автоматическое открытие следующей запланированной смены для сотрудника при закрытии предыдущей смены, если время окончания одной смены совпадает с началом следующей.

## Реализация

### Celery задача: `auto_close_shifts`
**Файл:** `core/celery/tasks/shift_tasks.py`  
**Расписание:** Каждые 30 минут (Celery Beat)

### Логика работы

#### 1. Автозакрытие смен
Задача обрабатывает два типа смен:

**Фактические смены (Shift):**
- Запрос: `SELECT * FROM shifts WHERE status='active' AND start_time < now`
- Проверяет время окончания:
  - Для запланированных (`is_planned=True`): берет `end_time` из тайм-слота
  - Для спонтанных: берет `closing_time` объекта
- Если текущее время ≥ времени окончания → закрывает смену

**Запланированные смены (ShiftSchedule):**
- Запрос: `SELECT * FROM shift_schedules WHERE status='confirmed' AND planned_start < now AND auto_closed=False`
- **Примечание:** Статус `'confirmed'` - это legacy/резерв, реально используется `'planned'`
- Проверяет время окончания (приоритет):
  1. `end_time` тайм-слота
  2. `closing_time` объекта
  3. `auto_close_minutes` объекта
- Если текущее время ≥ времени окончания → закрывает смену

#### 2. Автооткрытие следующей смены

**Условия срабатывания:**
1. Смена закрылась **автоматически** в текущем выполнении задачи
2. У сотрудника есть следующая запланированная смена (`status='planned'`) в этот же день
3. Время совпадает: `end_time` закрытой смены == `start_time` следующей (проверка через тайм-слоты)

**Процесс открытия:**
```python
# 1. Обновление статуса текущей смены
current_schedule.status = 'completed'

# 2. Поиск следующей смены
next_schedule = SELECT * FROM shift_schedules 
                WHERE user_id=X 
                AND status='planned' 
                AND date(planned_start)=today 
                ORDER BY planned_start LIMIT 1

# 3. Проверка совпадения времени
if prev_timeslot.end_time == next_timeslot.start_time:
    # 4. Создание новой смены
    new_shift = Shift(
        user_id=user_id,
        object_id=object_id,
        start_time=timeslot.start_time,  # Время начала тайм-слота!
        actual_start=now(),               # Фактическое время открытия
        planned_start=timeslot.start_time + late_threshold,
        status='active',
        start_coordinates=prev_shift.start_coordinates,  # Координаты предыдущей
        hourly_rate=schedule.hourly_rate,
        time_slot_id=timeslot_id,
        schedule_id=schedule_id,
        is_planned=True
    )
    
    # 5. Обновление статуса расписания
    next_schedule.status = 'in_progress'
```

### Важные моменты

**Время смены:**
- `start_time` = время начала тайм-слота (НЕ текущее время)
- `actual_start` = фактическое время автооткрытия
- `planned_start` = время тайм-слота + `late_threshold_minutes`

**Координаты:**
- Используются координаты из предыдущей смены
- Не требуется повторная отправка геопозиции от сотрудника

**Ручное закрытие:**
- Автооткрытие НЕ срабатывает при ручном закрытии смены
- Работает ТОЛЬКО при автозакрытии через Celery

**Late threshold:**
- Используется `late_threshold_minutes` из объекта
- Обход иерархии `org_unit.parent` не используется (для избежания greenlet ошибок)

### Логирование

**При успешном автооткрытии:**
```
Auto-opened consecutive shift (from Shift): 
  user_id=7, user_telegram_id=1220971779, 
  prev_shift_id=377, next_schedule_id=370, 
  prev_time=21:30:00-21:40:00, 
  next_time=21:40:00-21:50:00, 
  object_id=9
```

**При отсутствии следующей смены:**
```
No next planned shift found for user_id=7 on date=2025-10-18
```

**При несовпадении времени:**
```
Time mismatch for consecutive shifts: 
  prev_end=21:40:00, next_start=21:50:00
```

## Обновленные модели

### Shift
- `start_time` - время начала тайм-слота (для автооткрытых смен)
- `actual_start` - фактическое время начала работы
- `planned_start` - плановое время с учетом порога опоздания

### ShiftSchedule
- `status` может быть: `planned`, `confirmed`, `in_progress`, `completed`, `cancelled`
- **Примечание:** `confirmed` практически не используется, основной статус - `planned`

## Связанные компоненты

- **Celery Beat:** Планировщик задач (`core/celery/celery_app.py`)
- **Shift Service:** Обычное открытие смен (`apps/bot/services/shift_service.py`)
- **Schedule Service:** Планирование смен (`shared/services/schedule_service.py`)
- **ObjectOpening:** Автозакрытие объектов при отсутствии активных смен

## Возможные улучшения

1. Добавить уведомление сотруднику о автооткрытии смены
2. Реализовать поддержку `org_unit.parent` для `late_threshold` (требует рефакторинга eager loading)
3. Удалить или реализовать использование статуса `confirmed` для ShiftSchedule
4. Добавить метрики и мониторинг автооткрытий

