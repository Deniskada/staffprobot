# Итерация 47: Учёт даты увольнения при определении активности контракта

## Проблема

При расторжении договора с указанием `termination_date` (например, 22.11) сотрудник сразу становится неактивным для бота и не может открывать смены до даты увольнения. При этом владелец уже не может сформировать расчётный лист, так как сотрудник ещё считается активным.

## Цель

Сотрудник должен оставаться активным для:
- Планирования смен (веб-интерфейс)
- Открытия смен (бот)
- До даты увольнения (`termination_date`)

Но при этом владелец должен иметь возможность сформировать расчётный лист сразу после расторжения договора.

## Решение

### Логика определения активности контракта

**Контракт активен для работы (бот, планирование смен), если:**
- `status == 'active'` 
- `is_active == True`
- `termination_date IS NULL` ИЛИ `termination_date > today()`

**Контракт считается "уволенным" для расчётного листа, если:**
- `status == 'terminated'` ИЛИ
- (`status == 'active'` И `termination_date IS NOT NULL`)

## План изменений

### Фаза 1: Создание helper-функции (0.5 дня)

**Файл:** `shared/services/contract_validation_service.py` (новый)

```python
from datetime import date
from domain.entities.contract import Contract
from sqlalchemy import and_, or_

def is_contract_active_for_work(contract: Contract, check_date: date = None) -> bool:
    """
    Проверяет, активен ли контракт для работы (открытие смен, планирование).
    
    Контракт активен, если:
    - status == 'active'
    - is_active == True
    - termination_date IS NULL ИЛИ termination_date > check_date
    
    Args:
        contract: Объект Contract
        check_date: Дата для проверки (по умолчанию сегодня)
    
    Returns:
        True, если контракт активен для работы
    """
    if check_date is None:
        check_date = date.today()
    
    if contract.status != 'active' or not contract.is_active:
        return False
    
    # Если termination_date не указан - контракт активен
    if contract.termination_date is None:
        return True
    
    # Если termination_date указан - контракт активен только до этой даты
    return contract.termination_date > check_date


def is_contract_terminated_for_payroll(contract: Contract) -> bool:
    """
    Проверяет, считается ли контракт уволенным для расчётного листа.
    
    Контракт считается уволенным, если:
    - status == 'terminated' ИЛИ
    - (status == 'active' И termination_date IS NOT NULL)
    
    Args:
        contract: Объект Contract
    
    Returns:
        True, если контракт считается уволенным
    """
    if contract.status == 'terminated':
        return True
    
    if contract.status == 'active' and contract.termination_date is not None:
        return True
    
    return False


def build_active_contract_filter(check_date: date = None):
    """
    Создаёт SQLAlchemy фильтр для активных контрактов (для работы).
    
    Args:
        check_date: Дата для проверки (по умолчанию сегодня)
    
    Returns:
        SQLAlchemy условие для фильтрации
    """
    if check_date is None:
        from datetime import date
        check_date = date.today()
    
    return and_(
        Contract.status == 'active',
        Contract.is_active == True,
        or_(
            Contract.termination_date.is_(None),
            Contract.termination_date > check_date
        )
    )
```

### Фаза 2: Обновление проверок в боте (0.5 дня)

**Файл:** `apps/bot/services/shift_service.py`

**Изменения:**
- Заменить проверку `Contract.status == 'active'` и `Contract.is_active == True` на использование `build_active_contract_filter()`
- Добавить проверку `termination_date` в запрос контракта

**Строки:** ~176-183

```python
from shared.services.contract_validation_service import build_active_contract_filter
from datetime import date

# Было:
contract_query = select(Contract).where(
    and_(
        Contract.employee_id == db_user.id,
        Contract.status == 'active',
        Contract.is_active == True,
        cast(Contract.allowed_objects, JSONB).op('@>')(cast([object_id], JSONB))
    )
)

# Станет:
contract_query = select(Contract).where(
    and_(
        Contract.employee_id == db_user.id,
        build_active_contract_filter(date.today()),
        cast(Contract.allowed_objects, JSONB).op('@>')(cast([object_id], JSONB))
    )
)
```

### Фаза 3: Обновление проверок при планировании смен (0.5 дня)

**Файлы:**
- `apps/web/routes/owner.py` - `check_employee_availability_owner`
- `apps/web/routes/manager.py` - аналогичные проверки
- `apps/web/routes/calendar.py` - `api_calendar_plan_shift`

**Изменения:**
- Заменить проверки `Contract.status == 'active'` на использование `build_active_contract_filter()`
- Убедиться, что проверка выполняется для даты планируемой смены, а не только сегодня

### Фаза 4: Обновление проверок доступа к объектам (0.5 дня)

**Файл:** `shared/services/object_access_service.py`

**Изменения:**
- Заменить проверку `Contract.status == "active"` на использование `build_active_contract_filter()`

### Фаза 5: Обновление логики расчётного листа (0.3 дня)

**Файлы:**
- `apps/web/routes/payroll.py` - `owner_payroll_list`
- `apps/web/routes/manager_payroll.py` - `manager_payroll_list`

**Изменения:**
- Использовать `is_contract_terminated_for_payroll()` вместо проверки только `is_active == False`
- Сотрудник считается уволенным, если есть контракт с `termination_date IS NOT NULL`, даже если `status == 'active'`

**Текущая логика (строка 368-384):**
```python
contracts_status_query = select(Contract.employee_id, Contract.is_active, Contract.status).where(Contract.owner_id == owner_id)
# ...
if is_active and status == 'active':
    active_employee_ids.add(emp_id)
```

**Новая логика:**
```python
from shared.services.contract_validation_service import is_contract_terminated_for_payroll

contracts_query = select(Contract).where(Contract.owner_id == owner_id)
contracts_result = await db.execute(contracts_query)
contracts = contracts_result.scalars().all()

active_employee_ids: set[int] = set()
for contract in contracts:
    emp_id = int(contract.employee_id)
    if emp_id not in summary_map:
        summary_map[emp_id] = {...}
    # Контракт активен для работы, если не уволен для расчётного листа
    if not is_contract_terminated_for_payroll(contract):
        active_employee_ids.add(emp_id)
```

### Фаза 6: Обновление других сервисов (0.5 дня)

**Файлы:**
- `apps/web/services/contract_service.py` - методы `get_active_contracts`, `get_employee_contracts`
- `apps/web/services/billing_service.py` - подсчёт сотрудников
- `apps/web/services/limits_service.py` - подсчёт лимитов
- `apps/web/services/tariff_service.py` - подсчёт сотрудников

**Изменения:**
- Заменить проверки `Contract.is_active == True` и `Contract.status == 'active'` на использование `build_active_contract_filter()`
- Для подсчёта лимитов использовать активные контракты (с учётом `termination_date`)

### Фаза 7: Тестирование (0.5 дня) ✅

**Статус:** Завершено 19.11.2025

**Сценарии:**
1. Расторжение договора с `termination_date = 22.11`, сегодня 19.11:
   - ✅ Сотрудник может открывать смены до 22.11
   - ✅ Сотрудник не может открывать смены после 22.11
   - ✅ Владелец видит кнопку "Расчётный лист" сразу после расторжения
   - ✅ Планирование смен работает до 22.11

2. Расторжение договора с `termination_date = сегодня`:
   - ✅ Сотрудник не может открывать смены сегодня
   - ✅ Владелец видит кнопку "Расчётный лист"

3. Расторжение договора без `termination_date` (статус `terminated`):
   - ✅ Сотрудник не может открывать смены
   - ✅ Владелец видит кнопку "Расчётный лист"

**Результаты тестирования:**
- ✅ Все функции `contract_validation_service.py` работают корректно
- ✅ Интеграции в боте и веб-интерфейсе применены
- ✅ SQL фильтры создаются правильно
- ✅ Логика определения активности контракта работает как ожидается

### Фаза 8: Документация (0.2 дня) ✅

**Статус:** Завершено 19.11.2025

**Обновлённые файлы:**
- ✅ `doc/plans/ITERATION_47_CONTRACT_TERMINATION_DATE.md` - добавлен статус завершения
- ✅ `doc/plans/roadmap.md` - итерация 47 отмечена как завершённая
- ✅ `shared/services/contract_validation_service.py` - полная документация в docstrings

## Статус выполнения

**✅ Итерация 47 завершена (19.11.2025)**

Все фазы выполнены:
- ✅ Фаза 1: Создан `contract_validation_service.py`
- ✅ Фаза 2: Обновлены проверки в боте
- ✅ Фаза 3: Обновлены проверки при планировании смен
- ✅ Фаза 4: Обновлены проверки доступа к объектам
- ✅ Фаза 5: Обновлена логика расчётного листа
- ✅ Фаза 6: Обновлены другие сервисы
- ✅ Фаза 7: Тестирование на dev
- ✅ Фаза 8: Документация

**Реализованные функции:**
- `is_contract_active_for_work()` - проверка активности для работы
- `is_contract_terminated_for_payroll()` - проверка увольнения для расчётного листа
- `build_active_contract_filter()` - SQL фильтр для активных контрактов

**Интеграции:**
- Бот: `apps/bot/services/shift_service.py`, `employee_objects_service.py`, `object_state_handlers.py`
- Веб: `apps/web/routes/owner.py`, `manager.py`, `payroll.py`, `manager_payroll.py`
- Сервисы: `object_access_service.py`, `billing_service.py`, `limits_service.py`, `tariff_service.py`

## Итоговая оценка

**Общее время:** 3.5 дня

**Критичность:** Высокая (влияет на работу сотрудников и расчётные листы)

## Риски

1. **Миграция данных:** Существующие контракты с `termination_date` могут вести себя неожиданно
2. **Производительность:** Добавление проверки `termination_date` в запросы может замедлить их
3. **Обратная совместимость:** Нужно убедиться, что старые контракты без `termination_date` работают корректно

## Примечания

- Все изменения должны быть обратно совместимы
- Проверка `termination_date` должна учитывать часовой пояс (использовать `date.today()` в UTC или локальном времени)
- Для планирования смен на будущую дату нужно проверять `termination_date` относительно даты планируемой смены, а не сегодня

