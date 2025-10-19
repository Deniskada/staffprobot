# Функция: Финальный расчёт при расторжении договора

## Назначение
Система финального расчёта позволяет владельцу/управляющему выбрать способ выплаты при увольнении сотрудника:
- **По графику** - начисления продолжают создаваться по регулярному графику выплат
- **В дату увольнения** - разовая выплата всех накопленных сумм в указанную дату

## Модель данных

### Contract (расширение)
**Новые поля:**
- `termination_date` (Date, nullable) - дата увольнения сотрудника
- `settlement_policy` (String(32), default='schedule') - режим финрасчёта
  - `'schedule'` - выплаты по графику
  - `'termination_date'` - разовая выплата в дату увольнения

### ContractTermination
**Назначение:** Хранение истории расторжений для аналитики

**Поля:**
- `id` (Integer, PK)
- `contract_id` (Integer, FK → contracts.id)
- `employee_id` (Integer, FK → users.id)
- `owner_id` (Integer, FK → users.id)
- `terminated_by_id` (Integer, FK → users.id)
- `terminated_by_type` (String(20)) - 'owner', 'manager', 'admin'
- `reason_category` (String(50)) - категория причины
  - 'violation' - Нарушение дисциплины
  - 'quality' - Недостаточное качество работы
  - 'agreement' - Соглашение сторон
  - 'initiative' - Инициатива сотрудника
  - 'reduction' - Сокращение штата
  - 'relocation' - Переезд
  - 'health' - Проблемы со здоровьем
  - 'other' - Другое
- `reason` (Text) - полная причина с категорией
- `termination_date` (Date, nullable)
- `settlement_policy` (String(32))
- `terminated_at` (DateTime)

## API Endpoints

### Owner

**POST /owner/employees/contract/{contract_id}/terminate**
- Form: `reason` (Text, required)
- Form: `reason_category` (String, required)
- Form: `termination_date` (Date, optional) - YYYY-MM-DD
- Form: `payout_mode` (String, default='schedule')
  - `'schedule'` → settlement_policy='schedule'
  - `'termination_date'` → settlement_policy='termination_date'

### Manager

**POST /manager/contracts/{contract_id}/terminate**
- Аналогичные параметры
- Проверка прав: manager должен иметь право на этого сотрудника

## Логика работы

### 1. Расторжение договора (ContractService)

**При расторжении:**
1. Обновление полей:
   - `status = 'terminated'`
   - `is_active = False`
   - `termination_date` (если указана)
   - `settlement_policy`
2. Создание записи в `contract_terminations`
3. Если указана `termination_date`:
   - Автоматическая отмена всех **плановых** смен после этой даты
   - Метод: `_cancel_shifts_after_termination_date()`

### 2. Начисления по графику (Celery Task)

**create_payroll_entries_by_schedule** (ежедневно 01:00)

Для каждого графика выплат:
1. Выбор объектов владельца
2. Выбор договоров:
   ```python
   or_(
       and_(Contract.status == 'active', Contract.is_active == True),
       and_(
           Contract.status == 'terminated',
           Contract.settlement_policy == 'schedule'
       )
   )
   ```
3. Для каждого сотрудника:
   - Получить неприменённые adjustments за период
   - Создать PayrollEntry
   - Отметить adjustments как применённые

### 3. Финальный расчёт (Celery Task)

**create_final_settlements_by_termination_date** (ежедневно 01:05)

Логика:
1. Найти договоры где:
   - `settlement_policy = 'termination_date'`
   - `termination_date = today`
2. Для каждого:
   - Получить ВСЕ неприменённые adjustments до `termination_date` (включительно)
   - Создать один PayrollEntry с:
     - `period_start = MIN(adjustment.created_at)`
     - `period_end = termination_date`
     - `payment_type = 'final_settlement'`
   - Отметить adjustments как применённые

## Celery конфигурация

**Beat schedule:**
```python
'create-final-settlements-by-termination-date': {
    'task': 'create_final_settlements_by_termination_date',
    'schedule': crontab(hour=1, minute=5),
}
```

**Routing:**
```python
'create_final_settlements_by_termination_date': {'queue': 'shifts'}
```

## UI Templates

### Owner
- `apps/web/templates/owner/employees/contract_detail.html`
  - Модальное окно расторжения с полями:
    - Категория причины (select)
    - Причина (textarea)
    - Дата увольнения (date, optional)
    - Режим выплаты (radio: график/дата увольнения)

### Manager
- `apps/web/templates/manager/employees/detail.html`
  - Аналогичные поля

## Аналитика

### Страница: /owner/analytics/cancellations

**Новая секция: Расторжения договоров**

Таблица:
- Сотрудник
- Дата расторжения
- Категория причины
- Причина
- Дата увольнения
- Режим финрасчёта
- Кем расторгнут

Статистика:
- Количество расторжений по категориям
- График динамики по месяцам

**Route:** `apps/web/routes/cancellations.py`
**Template:** `apps/web/templates/owner/analytics/cancellations.html`

## Зависимости

### Services
- `shared/services/payroll_adjustment_service.py`
  - `get_unapplied_adjustments()` - для графика
  - `get_unapplied_adjustments_until()` - для финрасчёта
- `apps/web/services/contract_service.py`
  - `terminate_contract()` - основная логика
  - `_cancel_shifts_after_termination_date()` - отмена смен

### Tasks
- `core/celery/tasks/payroll_tasks.py`
  - `create_payroll_entries_by_schedule()`
  - `create_final_settlements_by_termination_date()`

## Миграции

1. **7ea5d1851f43_add_contract_termination_fields.py**
   - Добавление `termination_date`, `settlement_policy` в `contracts`

2. **f7b35e4d704c_create_contract_terminations_table.py**
   - Создание таблицы `contract_terminations`

## Критические правила

1. **Не удалять adjustments** - они должны храниться для аудита
2. **settlement_policy по умолчанию = 'schedule'** - для старых договоров
3. **Финрасчёт запускается ПОСЛЕ обычных начислений** (01:05 vs 01:00)
4. **Проверка is_active в графиках** - обязательна для корректной работы
5. **Автоматическая отмена только ПЛАНОВЫХ смен** - спонтанные отменяются вручную

## Тестирование

### Сценарии
1. Расторжение с `settlement_policy='schedule'`:
   - ✅ Adjustments продолжают накапливаться
   - ✅ Выплаты создаются по вторникам
   
2. Расторжение с `settlement_policy='termination_date'`:
   - ✅ В указанную дату создаётся один PayrollEntry
   - ✅ Все adjustments до даты применяются
   
3. Отмена плановых смен:
   - ✅ Смены после termination_date отменяются
   - ✅ ShiftCancellation записи создаются

### Тестовые файлы
- `tests/integration/test_payroll_termination.py`

## Связанная документация
- [Contract](../entities/contract.md)
- [Payroll System](../entities/payroll.md)
- [Shift Cancellation](shift_cancellation.md)

