# Начисления и выплаты (Payroll)

## Описание

Система учета начислений, удержаний, доплат и выплат сотрудникам. Поддерживает автоматические удержания (опоздания, невыполненные задачи) и ручные корректировки.

## Модели данных

### 1. PayrollEntry (Начисление)

**Таблица:** `payroll_entries`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `employee_id` | Integer | FK → users.id |
| `period_start` | Date | Начало периода |
| `period_end` | Date | Конец периода |
| `base_amount` | Numeric(10,2) | Базовая сумма (за смены) |
| `bonus_amount` | Numeric(10,2) | Сумма доплат |
| `deduction_amount` | Numeric(10,2) | Сумма удержаний |
| `total_amount` | Numeric(10,2) | Итоговая сумма |
| `status` | String(20) | draft / approved / paid |
| `approved_at` | DateTime | Дата одобрения |
| `approved_by_id` | Integer | FK → users.id (кто одобрил) |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id (кто создал) |

### 2. PayrollDeduction (Удержание)

**Таблица:** `payroll_deductions`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `payroll_entry_id` | Integer | FK → payroll_entries.id |
| `amount` | Numeric(10,2) | Сумма удержания |
| `description` | Text | Описание |
| `is_automatic` | Boolean | Автоматическое (Celery) или ручное |
| `deduction_type` | String(50) | late_start / task_penalty / manual |
| `related_shift_id` | Integer | FK → shifts.id (если связано со сменой) |
| `metadata` | JSON | Дополнительная информация |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id |

### 3. PayrollBonus (Доплата/Премия)

**Таблица:** `payroll_bonuses`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `payroll_entry_id` | Integer | FK → payroll_entries.id |
| `amount` | Numeric(10,2) | Сумма доплаты |
| `description` | Text | Описание |
| `is_automatic` | Boolean | Автоматическая или ручная |
| `bonus_type` | String(50) | task_bonus / manual |
| `related_shift_id` | Integer | FK → shifts.id |
| `metadata` | JSON | Дополнительная информация |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id |

### 4. EmployeePayment (Выплата)

**Таблица:** `employee_payments`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `payroll_entry_id` | Integer | FK → payroll_entries.id |
| `amount` | Numeric(10,2) | Сумма выплаты |
| `payment_date` | Date | Дата выплаты |
| `payment_method` | String(50) | cash / card / bank_transfer |
| `notes` | Text | Примечания |
| `created_at` | DateTime | Дата записи |
| `created_by_id` | Integer | FK → users.id |

## Рабочий процесс

### 1. Создание начисления
```python
from apps.web.services.payroll_service import PayrollService

payroll_service = PayrollService(db)
entry = await payroll_service.create_payroll_entry(
    employee_id=100,
    period_start=date(2025, 10, 1),
    period_end=date(2025, 10, 31),
    created_by_id=owner_id
)
```

### 2. Автоматические удержания (Celery)
**Задача:** `process_automatic_deductions()` (ежедневно в 01:00)

**Логика:**
1. Найти все завершенные смены за вчера
2. Проверить опоздание → создать удержание (если превышен порог)
3. Проверить невыполненные задачи → создать штрафы/премии (только для "Повременно-премиальная")
4. Записать в `payroll_deductions` / `payroll_bonuses` с `is_automatic=True`

### 3. Ручные корректировки
```python
# Добавить удержание
await payroll_service.add_deduction(
    payroll_entry_id=1,
    amount=100.00,
    description="Штраф за нарушение",
    created_by_id=owner_id
)

# Добавить доплату
await payroll_service.add_bonus(
    payroll_entry_id=1,
    amount=500.00,
    description="Премия за переработку",
    created_by_id=owner_id
)
```

### 4. Одобрение
```python
await payroll_service.approve_payroll_entry(
    entry_id=1,
    approved_by_id=owner_id
)
# status: draft → approved
```

### 5. Запись выплаты
```python
await payroll_service.create_payment(
    payroll_entry_id=1,
    amount=5000.00,
    payment_method="bank_transfer",
    created_by_id=owner_id
)
# status: approved → paid
```

## Роли и права

### Владелец (Owner)
- ✅ Создание начислений
- ✅ Добавление удержаний/доплат
- ✅ Одобрение начислений
- ✅ Запись выплат
- ✅ Просмотр всех начислений

### Управляющий (Manager) с правом `can_manage_payroll`
- ✅ Просмотр начислений (по доступным объектам)
- ✅ Добавление удержаний/доплат (опционально)
- ✅ Одобрение начислений (опционально)
- ❌ Запись выплат (только владелец)

### Сотрудник (Employee)
- ✅ Просмотр своих начислений
- ✅ Просмотр истории выплат
- ❌ Изменение данных

## UI страницы

### Для владельца
- `/owner/payroll` - список начислений всех сотрудников
- `/owner/payroll/{entry_id}` - детализация с действиями
- `/owner/payroll/{entry_id}/add-deduction` - добавить удержание
- `/owner/payroll/{entry_id}/add-bonus` - добавить доплату

### Для управляющего
- `/manager/payroll` - список начислений (фильтр по доступным объектам)
- `/manager/payroll/{entry_id}` - детализация (только просмотр)

### Для сотрудника
- `/employee/payroll` - список своих начислений
- `/employee/payroll/{entry_id}` - детализация с историей выплат

## Автоматические процессы

### Celery задача: `process_automatic_deductions`
**Расписание:** Ежедневно в 01:00

**Логика:**
1. Выбрать все смены за вчера со статусом `completed`
2. Для каждой смены:
   - Проверить опоздание (используя настройки объекта/подразделения)
   - Проверить невыполненные обязательные задачи
   - Проверить выполненные необязательные задачи (премия)
3. Создать записи в `payroll_deductions` / `payroll_bonuses`

**Настройки берутся из:**
- `Object.get_effective_late_settings()` - с учетом наследования от подразделения
- `ShiftTask.deduction_amount` - сумма штрафа/премии за задачу

## Индексы

- `idx_payroll_entries_employee_id` - для быстрого поиска по сотруднику
- `idx_payroll_entries_period` - для фильтрации по датам
- `idx_payroll_entries_status` - для фильтрации по статусу
- `idx_payroll_deductions_entry_id` - связь с начислением
- `idx_payroll_bonuses_entry_id` - связь с начислением

## Связи

```
PayrollEntry
├── employee → User
├── approved_by → User
├── created_by → User
├── deductions → List[PayrollDeduction]
├── bonuses → List[PayrollBonus]
└── payments → List[EmployeePayment]

PayrollDeduction
├── payroll_entry → PayrollEntry
├── related_shift → Shift
└── created_by → User

PayrollBonus
├── payroll_entry → PayrollEntry
├── related_shift → Shift
└── created_by → User

EmployeePayment
├── payroll_entry → PayrollEntry
└── created_by → User
```

## См. также

- [Системы оплаты](payment_system.md)
- [Графики выплат](payment_schedule.md) (в разработке)
- [Задачи на смену](shift_task.md)
- [Организационная структура](org_structure.md)

