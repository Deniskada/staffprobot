# Bug: shift_schedule.status не обновляется при открытии/закрытии смены

**ID:** bug-shift-schedule-status-not-updated  
**Дата обнаружения:** 2025-10-12  
**Статус:** ✅ Исправлено  
**Приоритет:** Критичный  
**Теги:** `bot`, `shift-scheduling`, `database`, `business-logic`

---

## 🐛 Симптомы

1. **Множественное использование:** Один shift_schedule используется многократно (5+ раз)
2. **Статус не меняется:** schedule.status остается "planned" даже после использования
3. **Неактуальные предложения:** Бот предлагает вчерашние смены сегодня

**Пример:**
```sql
-- Schedule 277 использован 5 РАЗ:
SELECT s.id, s.status FROM shifts s WHERE s.schedule_id = 277;
-- 85 (completed), 86 (completed), 88 (completed), 89 (completed), 91 (active)

-- Но статус schedule 277 не обновлен:
SELECT status FROM shift_schedules WHERE id = 277;
-- status = 'planned' ❌
```

---

## 🔍 Воспроизведение

1. Создать shift_schedule на сегодня
2. Открыть смену через "Открыть смену" (используется этот schedule)
3. Закрыть смену
4. Попытаться снова открыть смену
5. **Баг:** Бот предлагает тот же самый schedule снова!

**Последствия:**
- Один schedule используется бесконечно
- Невозможно отследить "использованные" vs "доступные" смены
- После полуночи показываются вчерашние schedules

---

## 🔧 Корень проблемы

**Файлы:** 
- `apps/bot/services/shift_service.py::open_shift`
- `shared/services/shift_service.py::close_shift`

### Проблема 1: Статус не обновляется при открытии

```python
# apps/bot/services/shift_service.py:305
new_shift = Shift(
    # ... поля ...
    schedule_id=schedule_id if shift_type == "planned" else None,
    is_planned=shift_type == "planned"
)

session.add(new_shift)
await session.commit()  # ❌ Статус schedule НЕ обновлен!
```

### Проблема 2: Статус не обновляется при закрытии

```python
# shared/services/shift_service.py:188-197
active_shift.end_time = datetime.now()
active_shift.status = "completed"

# ... расчеты ...

await session.commit()  # ❌ Статус schedule НЕ обновлен!
```

---

## ✅ Решение

### 1. Обновление статуса при открытии смены

**Файл:** `apps/bot/services/shift_service.py`

```python
session.add(new_shift)

# Обновляем статус shift_schedule, если это запланированная смена
if shift_type == "planned" and schedule_id:
    from domain.entities.shift_schedule import ShiftSchedule
    schedule_query = select(ShiftSchedule).where(ShiftSchedule.id == schedule_id)
    schedule_result = await session.execute(schedule_query)
    schedule = schedule_result.scalar_one_or_none()
    
    if schedule:
        schedule.status = "in_progress"
        session.add(schedule)
        logger.info(
            f"Updated shift_schedule status to in_progress",
            schedule_id=schedule_id,
            shift_id=new_shift.id
        )

await session.commit()
```

### 2. Обновление статуса при закрытии смены

**Файл:** `shared/services/shift_service.py`

```python
# Закрываем смену
active_shift.end_time = datetime.now()
active_shift.status = "completed"

# ... расчеты ...

# Обновляем статус shift_schedule, если это была запланированная смена
if active_shift.is_planned and active_shift.schedule_id:
    from domain.entities.shift_schedule import ShiftSchedule
    schedule_query = select(ShiftSchedule).where(ShiftSchedule.id == active_shift.schedule_id)
    schedule_result = await session.execute(schedule_query)
    schedule = schedule_result.scalar_one_or_none()
    
    if schedule:
        schedule.status = "completed"
        session.add(schedule)
        logger.info(
            f"Updated shift_schedule status to completed",
            schedule_id=active_shift.schedule_id,
            shift_id=active_shift.id
        )

await session.commit()
```

### 3. Улучшение фильтра запланированных смен

**Файл:** `apps/bot/services/shift_schedule_service.py`

```python
# JOIN с time_slots для проверки slot_date (более надежно)
query = (
    select(ShiftSchedule)
    .join(TimeSlot, TimeSlot.id == ShiftSchedule.time_slot_id)
    .where(
        and_(
            ShiftSchedule.user_id == user.id,
            ShiftSchedule.status.in_(["planned", "confirmed"]),  # Исключает in_progress и completed
            TimeSlot.slot_date == target_date  # Проверяем slot_date, а не planned_start!
        )
    )
    .order_by(ShiftSchedule.planned_start)
)
```

### 4. Миграция данных (для старых schedules)

```sql
-- Обновляем статусы shift_schedules, которые уже использованы
UPDATE shift_schedules ss
SET status = 'completed'
FROM shifts s
WHERE s.schedule_id = ss.id
  AND s.status = 'completed'
  AND ss.status IN ('planned', 'confirmed', 'in_progress');
-- UPDATE 39
```

---

## 📦 Коммит

```
commit 5e64b54
Исправление управления статусами shift_schedule

Проблемы:
1. shift_schedule.status не обновлялся при открытии/закрытии смены
2. Один schedule использовался многократно (5 раз!)
3. Фильтр по planned_start мог включать неактуальные тайм-слоты

Решения:
1. При открытии смены: schedule.status → 'in_progress'
2. При закрытии смены: schedule.status → 'completed'  
3. Фильтр изменен: JOIN с time_slots и проверка slot_date (вместо planned_start)

Теперь каждый schedule используется только 1 раз
```

---

## 🧪 Тестирование

### До исправления:

```sql
-- Schedule 277 использован 5 раз:
SELECT s.id, s.status FROM shifts s WHERE s.schedule_id = 277;
/*
 id  | status  
-----+----------
  85 | completed
  86 | completed
  88 | completed
  89 | completed
  91 | active
*/

-- Но статус остается "planned":
SELECT status FROM shift_schedules WHERE id = 277;
-- status = 'planned'
```

### После исправления:

```sql
-- 1. Открытие смены обновляет статус на "in_progress"
-- 2. Закрытие смены обновляет статус на "completed"
-- 3. Фильтр исключает completed schedules

SELECT 
  ss.id,
  ss.status,
  ts.slot_date,
  COUNT(s.id) as shifts_count
FROM shift_schedules ss
JOIN time_slots ts ON ts.id = ss.time_slot_id
LEFT JOIN shifts s ON s.schedule_id = ss.id
WHERE ss.user_id = 14
GROUP BY ss.id, ss.status, ts.slot_date
ORDER BY ts.slot_date DESC
LIMIT 5;

/*
 id  |  status   | slot_date  | shifts_count 
-----+-----------+------------+--------------
 278 | completed | 2025-10-12 |            1  ✅ Один schedule = одна смена
 277 | completed | 2025-10-11 |            5  (исторический)
*/
```

---

## 📊 Последствия бага

**До исправления:**
- 39 shift_schedules имели некорректный статус
- Множественное использование одного schedule
- Неактуальные предложения в боте

**После исправления:**
- ✅ Каждый schedule используется ровно 1 раз
- ✅ Фильтр показывает только актуальные смены
- ✅ Нет предложений вчерашних смен

---

## 📚 Связанные задачи

- Bug #3: [outdated-timeslot-binding](./bug-outdated-timeslot-binding.md) - частично решается этим исправлением
- Roadmap: Phase 4C - Object State Management
- Testing: `tests/manual/OBJECT_STATE_AND_TIMESLOTS_TESTING.md` (Фаза 2.1)

---

## 💡 Lessons Learned

1. **Статусы важны:** Любая "планируемая" сущность должна менять статус при использовании
2. **Идемпотентность:** Операции должны быть защищены от повторного выполнения
3. **Фильтры:** Всегда проверять актуальность по бизнес-дате (`slot_date`), а не по техническим полям (`planned_start`)
4. **Миграция данных:** При изменении логики нужна миграция старых данных

---

## 🔗 См. также

- `domain/entities/shift_schedule.py` - модель ShiftSchedule
- `apps/bot/services/shift_service.py` - открытие смены
- `shared/services/shift_service.py` - закрытие смены
- `apps/bot/services/shift_schedule_service.py` - фильтр запланированных смен

