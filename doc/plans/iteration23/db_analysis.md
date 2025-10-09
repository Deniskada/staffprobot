# Анализ текущей структуры БД для Итерации 23

**Дата:** 2025-10-09  
**Статус:** Завершен  
**Задача:** 0.1. Анализ текущей структуры БД

## 1. Таблицы с полем `hourly_rate`

### 1.1. contracts (Договоры)
```python
hourly_rate = Column(Integer, nullable=True)  # Почасовая ставка в копейках
```
- **Тип:** Integer
- **Единицы:** копейки
- **Nullable:** True
- **Текущее использование:** НЕ используется в расчете выплат за смены
- **Проблема:** Другой тип данных по сравнению с остальными таблицами

### 1.2. time_slots (Тайм-слоты)
```python
hourly_rate = Column(Numeric(10, 2), nullable=True)  # Ставка для слота
```
- **Тип:** Numeric(10, 2)
- **Единицы:** рубли
- **Nullable:** True
- **Текущее использование:** Используется для спонтанных смен (приоритет 1)

### 1.3. objects (Объекты)
```python
hourly_rate = Column(Numeric(10, 2), nullable=False)  # Ставка объекта
```
- **Тип:** Numeric(10, 2)
- **Единицы:** рубли
- **Nullable:** False (обязательное поле)
- **Текущее использование:** Используется как fallback для всех смен (приоритет 2)

### 1.4. shifts (Смены)
```python
hourly_rate = Column(Numeric(10, 2), nullable=True)  # Сохраненная ставка
```
- **Тип:** Numeric(10, 2)
- **Единицы:** рубли
- **Nullable:** True
- **Текущее использование:** Сохраняется при открытии смены, используется для расчета `total_payment` при закрытии

### 1.5. shift_schedules (Запланированные смены)
```python
hourly_rate = Column(Numeric(10, 2), nullable=True)  # Ставка на момент планирования
```
- **Тип:** Numeric(10, 2)
- **Единицы:** рубли
- **Nullable:** True
- **Текущее использование:** Используется для запланированных смен (приоритет 1)

## 2. Текущая логика расчета выплат

### 2.1. Определение ставки при открытии смены

**Файл:** `apps/bot/services/shift_service.py:101-148`

#### Для запланированных смен (shift_type="planned"):
```python
# Приоритет 1: Ставка из запланированной смены
schedule_rate = schedule_data.get('hourly_rate')
if schedule_rate:
    hourly_rate = schedule_rate
else:
    # Приоритет 2: Ставка объекта
    hourly_rate = obj.hourly_rate
```

#### Для спонтанных смен (shift_type="spontaneous"):
```python
# Приоритет 1: Ставка из тайм-слота
available_timeslots = await self.timeslot_service.get_available_timeslots_for_date(...)
if available_timeslots:
    timeslot_rate = first_timeslot.get('hourly_rate')
    if timeslot_rate:
        hourly_rate = timeslot_rate
    else:
        hourly_rate = obj.hourly_rate
else:
    # Приоритет 2: Ставка объекта
    hourly_rate = obj.hourly_rate
```

**Итого, текущие приоритеты:**
1. **Запланированная смена:** `schedule.hourly_rate` → `object.hourly_rate`
2. **Спонтанная смена:** `timeslot.hourly_rate` → `object.hourly_rate`
3. **Ставка договора НЕ используется!**

### 2.2. Расчет выплаты при закрытии смены

**Файл:** `shared/services/shift_service.py:192-195`

```python
duration = active_shift.end_time - active_shift.start_time
hours = duration.total_seconds() / 3600
active_shift.total_hours = hours
active_shift.total_payment = hours * active_shift.hourly_rate
```

**Используется сохраненная ставка из `shift.hourly_rate`**

### 2.3. Сохранение ставки в смену

**Файл:** `apps/bot/services/shift_service.py:151-158`

```python
new_shift = Shift(
    user_id=user.id,
    object_id=object_id,
    start_time=datetime.now(),
    status='active',
    start_coordinates=coordinates,
    hourly_rate=hourly_rate,  # Сохраняется определенная ставка
    ...
)
```

## 3. Места использования `hourly_rate` в коде

### 3.1. Основные сервисы

#### apps/bot/services/shift_service.py
- **Строки 101-148:** Логика определения ставки при открытии смены
- **Строка 157:** Сохранение ставки в новую смену
- **Строка 186:** Возврат ставки в ответе API

#### shared/services/shift_service.py
- **Строка 100:** Сохранение ставки объекта в новую смену
- **Строка 195:** Расчет `total_payment` при закрытии смены
- **Строка 265:** Возврат ставки в списке смен

#### apps/web/services/object_service.py
- Создание/редактирование объектов (сохранение `hourly_rate`)
- Создание/редактирование тайм-слотов (сохранение `hourly_rate`)

#### shared/services/schedule_service.py
- Создание запланированных смен (сохранение `hourly_rate` из тайм-слота)

### 3.2. Отчеты и аналитика

#### shared/services/calendar_filter_service.py
- Отображение ставок в календаре

#### apps/web/services/pdf_service.py
- Генерация PDF отчетов с информацией о ставках

### 3.3. UI/Templates
- Отображение ставок в формах создания/редактирования:
  - Объектов
  - Тайм-слотов
  - Договоров

## 4. Выявленные проблемы

### 4.1. ❌ Критические проблемы

1. **Несоответствие типов данных:**
   - `contracts.hourly_rate` - Integer (копейки)
   - Все остальные - Numeric(10, 2) (рубли)
   - **Риск:** Ошибки при преобразовании, некорректные расчеты

2. **Ставка договора не используется:**
   - `contract.hourly_rate` игнорируется при открытии смены
   - Нет флага для приоритизации ставки договора
   - **Риск:** Несоответствие условиям договора

### 4.2. ⚠️ Потенциальные проблемы

1. **Отсутствие истории изменений ставок:**
   - Нет таблицы для хранения истории изменений ставок
   - Если ставка изменилась после открытия смены, это не отслеживается

2. **Нет валидации ставок:**
   - Нет проверки, что ставка > 0
   - Нет проверки, что ставка не превышает разумные пределы

3. **Сложная логика определения ставки:**
   - Логика разбросана по нескольким файлам
   - Сложно понять приоритеты без изучения кода

## 5. Рекомендации для изменений

### 5.1. Унификация типов данных

**Решение:** Изменить `contracts.hourly_rate` на `Numeric(10, 2)` (рубли)

**Миграция:**
```python
# Преобразование копеек в рубли
UPDATE contracts SET hourly_rate = hourly_rate / 100.0 WHERE hourly_rate IS NOT NULL;
ALTER TABLE contracts ALTER COLUMN hourly_rate TYPE NUMERIC(10, 2);
```

### 5.2. Добавление флага приоритета ставки договора

**Решение:** Добавить поле `use_contract_rate` (Boolean) в `contracts`

**Новая логика:**
```python
if contract.use_contract_rate and contract.hourly_rate:
    hourly_rate = contract.hourly_rate  # Приоритет 1
elif schedule.hourly_rate:
    hourly_rate = schedule.hourly_rate  # Приоритет 2
elif timeslot.hourly_rate:
    hourly_rate = timeslot.hourly_rate  # Приоритет 3
else:
    hourly_rate = object.hourly_rate    # Приоритет 4 (fallback)
```

### 5.3. Централизация логики определения ставки

**Решение:** Создать метод `determine_hourly_rate()` в `shared/services/shift_service.py`

**Преимущества:**
- Единое место для логики
- Легко тестировать
- Легко расширять

### 5.4. Добавление валидации

**Решение:** Добавить валидацию в сервисы:
```python
if hourly_rate <= 0:
    raise ValueError("Hourly rate must be greater than 0")
if hourly_rate > 10000:  # Макс ставка 10,000 руб/час
    raise ValueError("Hourly rate exceeds maximum allowed value")
```

## 6. Список мест для изменений

### 6.1. Модели (domain/entities/)
- ✅ `contract.py` - изменить тип `hourly_rate`, добавить `use_contract_rate`
- ✅ `object.py` - без изменений
- ✅ `time_slot.py` - без изменений
- ✅ `shift.py` - без изменений
- ✅ `shift_schedule.py` - без изменений

### 6.2. Миграции (migrations/versions/)
- ✅ Создать миграцию для изменения типа `contracts.hourly_rate`
- ✅ Создать миграцию для добавления `contracts.use_contract_rate`
- ✅ Скрипт миграции данных (копейки → рубли)

### 6.3. Сервисы
- ✅ `apps/bot/services/shift_service.py` - обновить логику определения ставки
- ✅ `shared/services/shift_service.py` - добавить метод `determine_hourly_rate()`
- ✅ `apps/web/services/contract_service.py` - добавить валидацию `use_contract_rate`

### 6.4. UI/Templates
- ✅ `apps/web/templates/owner/employees/create.html` - добавить чекбокс
- ✅ `apps/web/templates/owner/employees/edit_contract.html` - добавить чекбокс
- ✅ `apps/web/templates/owner/employees/detail.html` - отображать источник ставки

### 6.5. Тесты
- ✅ `tests/unit/test_contract_rate.py` - новые unit-тесты
- ✅ `tests/integration/test_shift_rate_priority.py` - новые integration-тесты

## 7. Метрики и оценки

**Количество файлов для изменения:** ~15  
**Количество строк кода:** ~500-700  
**Сложность изменений:** Средняя  
**Риск регрессии:** Средний (влияет на расчет выплат)

**Рекомендуемый порядок изменений:**
1. Миграция типа данных (contracts.hourly_rate)
2. Добавление флага use_contract_rate
3. Обновление логики в сервисах
4. Обновление UI
5. Тесты
6. Smoke-тесты на dev

---

**Следующая задача:** 0.2. Проектирование моделей данных

