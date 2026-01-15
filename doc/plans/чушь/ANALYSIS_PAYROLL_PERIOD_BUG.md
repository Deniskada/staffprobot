# Анализ проблемы с неправильным периодом начислений 18.11.2025

## Краткое резюме

**Дата**: 18.11.2025 (вторник)  
**Проблема**: Использован неправильный график с периодом **1-15 ноября** (15 дней) вместо правильного графика **id=2** с периодом **27.10-02.11** (7 дней)  
**Причина**: Код проходит по графикам в порядке их получения из БД и берет **последний найденный** график, который подходит для даты. Для графиков с `owner_id` код берет **ВСЕ объекты владельца**, игнорируя подразделения. Должно быть: найти подразделения, использующие график (с учетом наследования), затем найти объекты, входящие в эти подразделения.  
**Решение**: Исправить логику выбора объектов для графиков с `owner_id` - использовать подразделения вместо всех объектов владельца.

## Проблема

18.11.2025 (вторник) при создании начислений был использован **неправильный график** с периодом **1-15 ноября** (15 дней, start_offset=-15, end_offset=-1) вместо правильного графика **id=2** с периодом **27.10-02.11** (7 дней, start_offset=-22, end_offset=-16).

## Факты

1. **18.11.2025 - это вторник** (isoweekday=2, weekday=1)
2. **Основное подразделение** (id=1, owner_id=7) использует график выплат **id=2** (weekly, payment_day=2, вторник)
3. График id=2 имеет настройки:
   - frequency: `weekly`
   - payment_day: `2` (вторник)
   - payment_period: `{"type": "week", "duration": 7, "end_offset": -16, "description": "За 7 дней, смещение начала -22 дней", "start_offset": -22}`
   - owner_id: `7`
   - **Правильный период для 18.11**: 27.10-02.11 (7 дней)

4. График id=6 имеет настройки:
   - frequency: `monthly`
   - payment_day: `16`
   - payment_period: `{"type": "month", "payments": [{"end_offset": -1, "payment_num": 1, "start_offset": -15, "is_end_of_month": false, "is_start_of_month": true, "next_payment_date": "2025-11-16"}, ...]}`
   - owner_id: `7`
   - **Неправильный период для 18.11**: 1-15 ноября (15 дней) - если бы сработал

5. **Проблема**: Вместо графика id=2 использовался график id=6 (или другой график с периодом 15 дней)

## Анализ кода

### Функция `_get_payment_period_for_date` (строки 441-595)

Для **weekly** графиков:
```python
if schedule.frequency == 'weekly':
    target_weekday = target_date.weekday() + 1  # Конвертируем в 1-7
    if target_weekday != schedule.payment_day:
        return None  # Сегодня не день выплаты
```

**Проблема**: Если 18.11 - понедельник (weekday=0, target_weekday=1), а payment_day=2, то функция должна вернуть `None` и график должен быть пропущен.

### Для monthly графиков с новым форматом (строки 501-546)

```python
elif schedule.frequency == 'monthly':
    payments = period_config.get('payments', [])
    if payments:
        # Ищем выплату, у которой next_payment_date совпадает с target_date
        matching_payment = None
        for payment in payments:
            next_payment_str = payment.get('next_payment_date')
            if next_payment_str:
                next_payment = date.fromisoformat(next_payment_str)
                if next_payment == target_date:
                    matching_payment = payment
                    break
        
        if not matching_payment:
            return None  # Дата не совпадает ни с одной выплатой
```

**Проблема**: Если в массиве `payments` нет записи с `next_payment_date = "2025-11-18"`, функция вернет `None`.

### Для monthly графиков со старым форматом (строки 548-579)

```python
# СТАРЫЙ формат: обратная совместимость
if target_date.day != schedule.payment_day:
    return None

# Используем старый формат с прямыми offset'ами
start_offset = period_config.get('start_offset', -60)
end_offset = period_config.get('end_offset', -30)

period_start = target_date + timedelta(days=start_offset)
period_end = target_date + timedelta(days=end_offset)
```

**Проблема**: Если `target_date.day == schedule.payment_day` (например, 18.11 и payment_day=18), то используется старый формат с offset'ами, который может дать неправильный период.

## Причина проблемы

### Что произошло

1. Скрипт нашел два графика с `owner_id=7`, которые подходят для 18.11:
   - График id=2 (weekly, вторник) - правильный
   - Другой график (возможно, id=6 или другой) - неправильный

2. Код проходит по графикам в порядке их получения из БД (без сортировки)

3. **Взял последний найденный график** (по порядку в БД) и сделал начисления по нему

4. Для графика с `owner_id` код использует **неправильную логику** (строки 103-108):
   ```python
   if schedule.owner_id:
       objects_query = select(Object).where(
           Object.is_active == True,
           Object.owner_id == schedule.owner_id
       )
   ```
   - Берет **ВСЕ активные объекты владельца**, игнорируя подразделения

### Как должно быть

1. Скрипт анализирует график
2. Находит, что сегодня дата начисления (это сделано правильно)
3. **Составляет список подразделений, использующих этот график, с учетом наследования**
4. **Составляет список объектов, входящих в эти подразделения** (с учетом наследования - все дочерние подразделения)
5. Создает начисления только для объектов, которые используют этот график через подразделения

### Проблема в коде

**Текущая логика** (строки 103-108):
- Если у графика есть `owner_id`, берет ВСЕ объекты владельца
- Игнорирует подразделения и наследование

**Правильная логика**:
- Найти подразделения с `payment_schedule_id == schedule.id` (прямо или через наследование)
- Найти все объекты, входящие в эти подразделения (с учетом дочерних подразделений)
- Создать начисления только для этих объектов

### Почему использовался неправильный график

Код проходит по графикам в порядке их получения из БД. Если график id=6 (или другой) обрабатывается последним и подходит для 18.11 (возможно, через старый формат monthly или другую логику), то он создает начисления для ВСЕХ объектов владельца, перезаписывая начисления от графика id=2.

## Что нужно проверить

1. Какой график должен использоваться для выплаты 18.11 с периодом 27.10-02.11?
2. Есть ли в БД график с next_payment_date = "2025-11-18" и правильными offset'ами?
3. Правильно ли настроен график для "Основного подразделения"?

## План исправления

### 1. Проверка настроек графиков

Нужно проверить:
- Какой график должен использоваться для выплаты 18.11
- Какие offset'ы должны быть для периода 27.10-02.11:
  - Для выплаты 18.11: start_offset = -22, end_offset = -16
  - period_start = 2025-11-18 + (-22) = 2025-10-27 ✅
  - period_end = 2025-11-18 + (-16) = 2025-11-02 ✅

### 2. Исправление логики определения периода

**Проблема в коде**: Для monthly графиков с новым форматом код ищет точное совпадение `next_payment_date == target_date`. Если такой записи нет, график пропускается.

**Решение**: Нужно добавить логику для автоматического обновления `next_payment_date` после создания начислений, чтобы следующая выплата использовала правильную дату.

### 3. Откат неправильных начислений

Если начисления были созданы с неправильным периодом, нужно:
1. Найти все начисления с периодом 1-15 ноября, созданные 16.11
2. Удалить их (или пометить как удаленные)
3. Откатить связанные adjustments (is_applied = false, payroll_entry_id = null)
4. Создать новые начисления с правильным периодом 27.10-02.11

## План отката начислений

### Шаг 1: Найти неправильные начисления

```sql
-- Проверить, какие начисления были созданы с неправильным периодом 18.11
-- Период 1-15 ноября (15 дней) вместо правильного 27.10-02.11 (7 дней)
SELECT id, employee_id, object_id, period_start, period_end, 
       (period_end - period_start + 1) as period_days, 
       gross_amount, created_at
FROM payroll_entries
WHERE period_start = '2025-11-01' 
  AND period_end = '2025-11-15'
  AND DATE(created_at) = '2025-11-18'
ORDER BY created_at;
```

**Важно**: Если начислений за 18.11 нет, проверить другие даты:
```sql
-- Проверить все начисления с периодом 1-15 ноября
SELECT id, employee_id, object_id, period_start, period_end, 
       (period_end - period_start + 1) as period_days, 
       gross_amount, created_at
FROM payroll_entries
WHERE period_start = '2025-11-01' 
  AND period_end = '2025-11-15'
ORDER BY created_at DESC;
```

### Шаг 2: Сохранить список ID для отката

```sql
-- Сохранить список ID начислений для отката
-- ВАЖНО: Заменить дату на фактическую дату создания неправильных начислений
SELECT id INTO TEMP TABLE wrong_payroll_entries
FROM payroll_entries
WHERE period_start = '2025-11-01' 
  AND period_end = '2025-11-15'
  AND DATE(created_at) = '2025-11-18';  -- Или другая дата, если начисления созданы в другой день
```

### Шаг 3: Откатить adjustments

```sql
-- Откатить все adjustments, связанные с неправильными начислениями
UPDATE payroll_adjustments
SET is_applied = false,
    payroll_entry_id = null,
    updated_at = NOW()
WHERE payroll_entry_id IN (
    SELECT id FROM wrong_payroll_entries
);
```

**Важно**: Проверить количество откатанных adjustments:
```sql
SELECT COUNT(*) FROM payroll_adjustments
WHERE payroll_entry_id IN (SELECT id FROM wrong_payroll_entries);
```

### Шаг 4: Удалить неправильные начисления

```sql
-- Удалить неправильные начисления
DELETE FROM payroll_entries
WHERE id IN (SELECT id FROM wrong_payroll_entries);
```

### Шаг 5: Проверить результат

```sql
-- Убедиться, что начисления удалены
SELECT COUNT(*) FROM payroll_entries
WHERE period_start = '2025-11-01' 
  AND period_end = '2025-11-15'
  AND DATE(created_at) = '2025-11-18';  -- Или другая дата
-- Должно быть 0

-- Убедиться, что adjustments откатаны
SELECT COUNT(*) FROM payroll_adjustments
WHERE payroll_entry_id IN (SELECT id FROM wrong_payroll_entries);
-- Должно быть 0 (или все payroll_entry_id должны быть NULL)

-- Проверить, что adjustments правильно откатаны
SELECT COUNT(*) FROM payroll_adjustments
WHERE is_applied = false
  AND payroll_entry_id IS NULL
  AND id IN (
    SELECT adjustment_id FROM payroll_adjustments 
    WHERE payroll_entry_id IN (SELECT id FROM wrong_payroll_entries)
  );
```

### Шаг 6: Создать правильные начисления

**Вариант А**: Исправить настройки графика и дождаться следующего запуска (04:00 следующего дня)

**Вариант Б**: Создать начисления вручную через веб-интерфейс или скрипт

**Важно**: Перед созданием правильных начислений нужно:
1. **Исправить код** - добавить приоритизацию графиков (см. план изменений)
2. Убедиться, что график id=2 правильно настроен и будет использоваться для объектов "Основного подразделения"
3. Проверить, что период 27.10-02.11 будет правильно рассчитан по графику id=2
4. После исправления кода запустить задачу создания начислений вручную или дождаться следующего запуска (04:00 следующего дня)

## План изменений в коде

### 1. Исправить логику выбора объектов для графиков с owner_id (ПРИОРИТЕТ)

**Файл**: `core/celery/tasks/payroll_tasks.py`, функция `create_payroll_entries_by_schedule`, строки 103-108

**Проблема**: 
- Для графиков с `owner_id` код берет **ВСЕ активные объекты владельца** (строки 104-108)
- Игнорирует подразделения и наследование
- Должно быть: найти подразделения с этим графиком, затем найти объекты, входящие в эти подразделения

**Решение**: 
Исправить логику выбора объектов для графиков с `owner_id`:

1. **Найти подразделения с этим графиком** (с учетом наследования):
   - Найти подразделения с `payment_schedule_id == schedule.id`
   - Найти все дочерние подразделения (рекурсивно)
   - Использовать метод `get_inherited_payment_schedule_id()` для проверки наследования

2. **Найти объекты, входящие в эти подразделения**:
   - Найти объекты с `org_unit_id` в списке найденных подразделений
   - Учесть все дочерние подразделения

3. **Убрать логику "все объекты владельца"**:
   - Для графиков с `owner_id` использовать ту же логику, что и для графиков без `owner_id`
   - Находить объекты через подразделения, а не напрямую по `owner_id`

**Пример кода**:
```python
# УБРАТЬ эту логику (строки 103-108):
# if schedule.owner_id:
#     objects_query = select(Object).where(
#         Object.is_active == True,
#         Object.owner_id == schedule.owner_id
#     )
# else:
#     ...

# ЗАМЕНИТЬ на единую логику:
# 1. Найти подразделения с этим графиком (с учетом наследования)
from sqlalchemy.orm import selectinload

units_with_schedule = []

# Найти все подразделения владельца (если owner_id указан) или все подразделения
if schedule.owner_id:
    all_units_query = select(OrgStructureUnit).options(
        selectinload(OrgStructureUnit.parent)
    ).where(
        OrgStructureUnit.owner_id == schedule.owner_id,
        OrgStructureUnit.is_active == True
    )
else:
    all_units_query = select(OrgStructureUnit).options(
        selectinload(OrgStructureUnit.parent)
    ).where(
        OrgStructureUnit.is_active == True
    )

all_units_result = await session.execute(all_units_query)
all_units = all_units_result.scalars().all()

# Функция для рекурсивного поиска всех потомков подразделения
async def get_all_descendant_unit_ids(unit_id: int, session: AsyncSession) -> List[int]:
    """Рекурсивно найти все дочерние подразделения"""
    result = [unit_id]
    children_query = select(OrgStructureUnit.id).where(
        OrgStructureUnit.parent_id == unit_id,
        OrgStructureUnit.is_active == True
    )
    children_result = await session.execute(children_query)
    children_ids = [row[0] for row in children_result.all()]
    
    for child_id in children_ids:
        result.extend(await get_all_descendant_unit_ids(child_id, session))
    
    return result

# Проверить каждое подразделение
for unit in all_units:
    # Проверить, использует ли подразделение этот график (с учетом наследования)
    inherited_schedule_id = unit.get_inherited_payment_schedule_id()
    if inherited_schedule_id == schedule.id:
        # Добавить само подразделение и все его дочерние подразделения
        unit_ids = await get_all_descendant_unit_ids(unit.id, session)
        units_with_schedule.extend(unit_ids)

# Убрать дубликаты
units_with_schedule = list(set(units_with_schedule))

# 2. Найти объекты, входящие в эти подразделения
if units_with_schedule:
    objects_query = select(Object).where(
        Object.is_active == True,
        Object.org_unit_id.in_(units_with_schedule)
    )
else:
    # Если нет подразделений с этим графиком, не создавать начисления
    objects_query = select(Object).where(False)  # Пустой результат
```

**Важно**: 
- Использовать `selectinload(OrgStructureUnit.parent)` для загрузки связей parent
- Метод `get_inherited_payment_schedule_id()` уже реализован в `OrgStructureUnit` и учитывает наследование
- Все подразделения входят в "Основное подразделение", поэтому все объекты должны соответствовать графику основного подразделения

### 2. Исправить логику определения периода для monthly графиков

**Файл**: `core/celery/tasks/payroll_tasks.py`, функция `_get_payment_period_for_date`

**Проблема**: 
- Код ищет точное совпадение `next_payment_date == target_date`
- Если такой записи нет, график пропускается
- Не обновляется `next_payment_date` после создания начислений

**Решение**: 
1. **Добавить автоматическое обновление `next_payment_date`** после создания начислений:
   - После успешного создания начислений обновить `next_payment_date` в массиве `payments`
   - Рассчитать следующую дату выплаты на основе frequency и payment_day
   - Сохранить обновленный `payment_period` в БД

2. **Добавить fallback логику** для monthly графиков:
   - Если в массиве `payments` нет записи с `next_payment_date == target_date`
   - Проверить, совпадает ли `target_date.day == schedule.payment_day`
   - Если совпадает, использовать первый payment из массива (или payment с минимальным `next_payment_date`)

**Пример кода**:
```python
# После создания начислений (в функции create_payroll_entries_by_schedule)
if schedule.frequency == 'monthly' and schedule.payment_period.get('payments'):
    payments = schedule.payment_period['payments']
    for payment in payments:
        if payment.get('next_payment_date') == today.isoformat():
            # Обновить next_payment_date на следующую дату
            # Логика зависит от frequency и payment_day
            # Например, для monthly: следующая выплата через месяц
            next_date = today + timedelta(days=30)  # или использовать calendar
            payment['next_payment_date'] = next_date.isoformat()
            break
    
    # Сохранить обновленный payment_period
    schedule.payment_period = {'payments': payments, ...}
    session.add(schedule)
    await session.flush()
```

### 3. Добавить валидацию периода

**Проблема**: Нет проверки, что рассчитанный период соответствует ожидаемому.

**Решение**: 
- Добавить проверку, что `period_start < period_end`
- Добавить проверку, что период не слишком большой (например, не более 60 дней)
- Логировать предупреждения, если период выходит за ожидаемые границы

**Пример кода**:
```python
period_start = payment_period['period_start']
period_end = payment_period['period_end']

# Валидация
if period_start > period_end:
    logger.error(f"Invalid period: start > end", 
                 period_start=period_start, period_end=period_end)
    continue

period_days = (period_end - period_start).days
if period_days > 60:
    logger.warning(f"Period too long: {period_days} days",
                   period_start=period_start, period_end=period_end)
```

### 4. Улучшить логирование

**Проблема**: Недостаточно информации в логах для диагностики проблем.

**Решение**: Добавить детальное логирование:
- Какой график использовался (id, name, frequency)
- Какие offset'ы были применены
- Какой период был рассчитан
- Почему график был выбран или пропущен
- Какие adjustments были найдены и применены

**Пример кода**:
```python
logger.info(
    "Processing schedule",
    schedule_id=schedule.id,
    schedule_name=schedule.name,
    frequency=schedule.frequency,
    payment_day=schedule.payment_day,
    target_date=today.isoformat(),
    period_start=period_start.isoformat(),
    period_end=period_end.isoformat(),
    start_offset=start_offset,
    end_offset=end_offset,
    matching_payment=matching_payment if matching_payment else None
)
```

### 5. Добавить проверку настроек графика перед использованием

**Проблема**: Нет проверки, что график правильно настроен.

**Решение**: 
- Проверить, что для monthly графиков есть массив `payments`
- Проверить, что в массиве есть хотя бы одна запись с `next_payment_date`
- Логировать предупреждения, если график настроен неправильно

**Пример кода**:
```python
if schedule.frequency == 'monthly':
    payments = period_config.get('payments', [])
    if not payments:
        logger.warning(f"Monthly schedule {schedule.id} has no payments array")
        continue
    
    # Проверить, что есть хотя бы одна запись с next_payment_date
    has_valid_payment = any(
        p.get('next_payment_date') for p in payments
    )
    if not has_valid_payment:
        logger.warning(f"Monthly schedule {schedule.id} has no valid payment dates")
        continue
```

## Итоговые выводы

### Причина проблемы

1. **18.11.2025 - вторник, график id=2 должен был сработать**:
   - График id=2 (weekly, payment_day=2, вторник) правильно настроен для выплаты 18.11
   - Правильный период: 27.10-02.11 (7 дней, start_offset=-22, end_offset=-16)

2. **Вместо графика id=2 использовался другой график**:
   - Созданы начисления с периодом 1-15 ноября (15 дней)
   - Это соответствует графику с настройками: start_offset=-15, end_offset=-1
   - График id=6 имеет такие настройки, но не должен был сработать 18.11

3. **Проблема в логике выбора объектов для графиков с owner_id**:
   - Скрипт нашел два графика с `owner_id=7`, которые подходят для 18.11
   - Взял последний найденный график (по порядку в БД) и сделал начисления по нему
   - Для графиков с `owner_id` код берет **ВСЕ активные объекты владельца**, игнорируя подразделения
   - Должно быть: найти подразделения, использующие график (с учетом наследования), затем найти объекты, входящие в эти подразделения

### Что нужно исправить

1. **В коде - исправить логику выбора объектов для графиков с owner_id** (ПРИОРИТЕТ):
   - Убрать логику "все объекты владельца" для графиков с `owner_id`
   - Найти подразделения, использующие график (с учетом наследования через `get_inherited_payment_schedule_id()`)
   - Найти все дочерние подразделения рекурсивно
   - Найти объекты, входящие в эти подразделения
   - Создать начисления только для объектов, которые используют график через подразделения

2. **В коде - добавить проверку обработанных объектов**:
   - Если несколько графиков подходят для одной даты, проверять, не обработан ли уже объект другим графиком
   - Добавить логирование, какой график использовался для каждого объекта
   - Добавить валидацию: если для одной даты подходят несколько графиков, логировать предупреждение

3. **Откатить неправильные начисления**:
   - Найти начисления с периодом 1-15 ноября, созданные 18.11 (или другим неправильным графиком)
   - Откатить связанные adjustments
   - Создать правильные начисления с периодом 27.10-02.11 по графику id=2

### Рекомендации

1. **Перед откатом**:
   - Сделать бэкап БД
   - Проверить, что все начисления с периодом 1-15 ноября действительно неправильные
   - Убедиться, что нет зависимостей от этих начислений

2. **После отката**:
   - Исправить настройки графика
   - Создать правильные начисления
   - Проверить, что все adjustments правильно применены

3. **Для предотвращения проблем в будущем**:
   - Исправить логику выбора объектов для графиков с `owner_id` (использовать подразделения)
   - Добавить проверку обработанных объектов
   - Улучшить логирование для диагностики

