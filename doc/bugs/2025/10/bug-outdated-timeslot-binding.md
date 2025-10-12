# Bug: Привязка к неактуальному тайм-слоту при "Открыть объект"

**ID:** bug-outdated-timeslot-binding  
**Дата обнаружения:** 2025-10-12  
**Статус:** ✅ Исправлено (см. bug-shift-schedule-status-not-updated)  
**Приоритет:** Средний  
**Теги:** `bot`, `shift-scheduling`, `timezone`, `business-logic`

---

## 🐛 Симптомы

При нажатии "🏢 Открыть объект" в 00:33 МСК 12 октября смена привязалась к тайм-слоту от 11 октября (22:55-23:55):

```sql
-- Смена 91:
- Фактически открыта: 2025-10-12 00:33 МСК
- Привязана к тайм-слоту: 1166 (slot_date = 2025-10-11, start_time = 22:55)
- Результат: date_check = MISMATCH
```

**Проблема:** Тайм-слот уже "прошел" (закончился 11 октября в 23:55), но система все равно предлагает его для открытия на следующий день.

---

## 🔍 Воспроизведение

1. Создать тайм-слот на сегодня: 22:00-23:00
2. Подождать до 00:30 следующего дня (после полуночи)
3. Нажать "🏢 Открыть объект"
4. Система предложит вчерашний тайм-слот, т.к. `get_user_planned_shifts_for_date(today)` ищет по `planned_start`, а не по `slot_date`

**SQL для проверки:**
```sql
SELECT 
  s.id,
  s.time_slot_id,
  ts.slot_date,
  DATE(s.start_time AT TIME ZONE 'Europe/Moscow') as actual_date,
  CASE 
    WHEN DATE(s.start_time AT TIME ZONE 'Europe/Moscow') = ts.slot_date 
    THEN 'OK' 
    ELSE 'MISMATCH' 
  END as status
FROM shifts s
JOIN time_slots ts ON ts.id = s.time_slot_id
WHERE s.id = 91;

-- Результат: MISMATCH
```

---

## 🔧 Корень проблемы

**Файл:** `apps/bot/services/shift_schedule_service.py:42-56`

```python
# Получаем запланированные смены пользователя на указанную дату
# Локализуем дату в Europe/Moscow для правильного сравнения
import pytz
msk_tz = pytz.timezone('Europe/Moscow')
start_of_day = msk_tz.localize(datetime.combine(target_date, datetime.min.time()))
end_of_day = start_of_day + timedelta(days=1)

query = select(ShiftSchedule).where(
    and_(
        ShiftSchedule.user_id == user.id,
        ShiftSchedule.status.in_(["planned", "confirmed"]),
        ShiftSchedule.planned_start >= start_of_day,  # ❌ Проблема здесь
        ShiftSchedule.planned_start < end_of_day
    )
).order_by(ShiftSchedule.planned_start)
```

**Проблемы:**
1. Фильтр по `planned_start` (время начала смены в UTC/MSK)
2. Не проверяется `slot_date` тайм-слота
3. Смены, начавшиеся вчера вечером, но с `planned_start` попадающим в диапазон сегодня, проходят фильтр

**Пример:**
- Сегодня: 12 октября, 00:30 МСК
- Тайм-слот 1166: slot_date = 11 октября, start_time = 22:55
- `planned_start` хранится как `2025-10-11 22:55:00+03`
- Фильтр ищет смены где `planned_start >= 2025-10-12 00:00:00+03`
- Но из-за timezone логики или других причин тайм-слот попадает в выборку

---

## ✅ Решение (предложение)

### Вариант 1: Проверка актуальности в `_handle_open_object`

```python
# В apps/bot/handlers_div/core_handlers.py
# После получения planned_shifts:

from datetime import date
today = date.today()

# Фильтруем только актуальные на сегодня
actual_planned_shifts = []
for shift_data in planned_shifts:
    # Получаем тайм-слот
    timeslot_id = shift_data.get('time_slot_id')
    if timeslot_id:
        # Проверяем slot_date тайм-слота
        async with get_async_session() as session:
            ts_query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
            ts_result = await session.execute(ts_query)
            timeslot = ts_result.scalar_one_or_none()
            
            if timeslot and timeslot.slot_date == today:
                actual_planned_shifts.append(shift_data)

planned_shifts = actual_planned_shifts
```

### Вариант 2: Улучшить фильтр в `shift_schedule_service.py`

```python
# Добавить JOIN с time_slots и проверку slot_date
query = (
    select(ShiftSchedule)
    .join(TimeSlot, TimeSlot.id == ShiftSchedule.time_slot_id)
    .where(
        and_(
            ShiftSchedule.user_id == user.id,
            ShiftSchedule.status.in_(["planned", "confirmed"]),
            TimeSlot.slot_date == target_date,  # ✅ Проверка slot_date!
        )
    )
    .order_by(ShiftSchedule.planned_start)
)
```

**Рекомендация:** Вариант 2 более надежный, т.к. фильтрует на уровне БД.

---

## 📦 Коммит

(Еще не исправлено)

---

## 🧪 Тестирование

**До исправления:**
```sql
-- В 00:30 12 октября бот предлагает тайм-слот от 11 октября
SELECT * FROM shift_schedules WHERE time_slot_id = 1166;
-- Попадает в выборку, хотя slot_date = 2025-10-11
```

**После исправления:**
```sql
-- В 00:30 12 октября бот НЕ предлагает вчерашние тайм-слоты
-- Только тайм-слоты с slot_date = 2025-10-12
```

---

## 📚 Связанные задачи

- Testing: `tests/manual/OBJECT_STATE_AND_TIMESLOTS_TESTING.md` (Фаза 2.1.А)
- Roadmap: Phase 4C - Object State Management

---

## 💡 Lessons Learned

1. **Timezone сложность:** Даты в БД и фильтры должны быть согласованы
2. **Бизнес-логика:** "Запланированная смена на сегодня" != "смена с planned_start сегодня"
3. **Актуальность:** Всегда проверять `slot_date` для тайм-слотов, а не только `planned_start`

---

## 🔗 См. также

- `apps/bot/services/shift_schedule_service.py` - фильтр запланированных смен
- `apps/bot/handlers_div/core_handlers.py` - логика "Открыть объект"
- `domain/entities/time_slot.py` - модель TimeSlot с slot_date

