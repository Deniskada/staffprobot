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
| `contract_id` | Integer | FK → contracts.id |
| `object_id` | Integer | FK → objects.id (основной объект) |
| `period_start` | Date | Начало периода |
| `period_end` | Date | Конец периода |
| `hours_worked` | Numeric(8,2) | Количество отработанных часов |
| `hourly_rate` | Numeric(10,2) | Часовая ставка |
| `gross_amount` | Numeric(10,2) | Базовая сумма (hours_worked × hourly_rate) |
| `total_bonuses` | Numeric(10,2) | Сумма доплат |
| `total_deductions` | Numeric(10,2) | Сумма удержаний |
| `net_amount` | Numeric(10,2) | Итоговая сумма к выплате |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id (кто создал, NULL если автоматически) |

**Примечание:** Поле `status` удалено. Статус начисления определяется по связанным выплатам (EmployeePayment).

### 2. PayrollAdjustment (Корректировки: удержания и доплаты)

**Таблица:** `payroll_adjustments`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `payroll_entry_id` | Integer | FK → payroll_entries.id |
| `amount` | Numeric(10,2) | Сумма (положительная для доплат, отрицательная для удержаний) |
| `description` | Text | Описание |
| `adjustment_type` | String(50) | shift_base / late_start / task_bonus / task_penalty / manual_bonus / manual_deduction |
| `related_shift_id` | Integer | FK → shifts.id (если связано со сменой) |
| `related_task_id` | Integer | FK → shift_tasks.id (если связано с задачей) |
| `is_applied` | Boolean | Применено ли к начислению |
| `metadata` | JSONB | Дополнительная информация |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id (NULL если автоматически) |

**Типы корректировок:**
- `shift_base` - базовая оплата за смену (автоматически)
- `late_start` - удержание за опоздание (автоматически)
- `task_bonus` - премия за выполнение задачи (автоматически)
- `task_penalty` - штраф за невыполнение задачи (автоматически)
- `manual_bonus` - ручная доплата (владелец/управляющий)
- `manual_deduction` - ручное удержание (владелец/управляющий)
- `incident_deduction` - удержание за ущерб по инциденту (автоматически при создании инцидента с суммой ущерба)
- `incident_refund` - возврат удержания по инциденту (автоматически при переводе инцидента в статус «resolved»)

### 3. EmployeePayment (Выплата)

**Таблица:** `employee_payments`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `payroll_entry_id` | Integer | FK → payroll_entries.id |
| `amount` | Numeric(10,2) | Сумма выплаты |
| `payment_date` | Date | Дата выплаты |
| `payment_method` | String(50) | cash / card / bank_transfer |
| `status` | String(20) | pending / completed / cancelled |
| `confirmation_code` | String(100) | Код подтверждения (номер транзакции, чек и т.д.) |
| `notes` | Text | Примечания |
| `created_at` | DateTime | Дата создания записи |
| `created_by_id` | Integer | FK → users.id |
| `completed_at` | DateTime | Дата подтверждения выплаты |
| `completed_by_id` | Integer | FK → users.id (кто подтвердил) |

**Статусы выплаты:**
- `pending` - выплата запланирована, ожидает подтверждения
- `completed` - выплата произведена и подтверждена
- `cancelled` - выплата отменена

## Рабочий процесс

### 1. Автоматическое создание начислений (Celery)
**Задача:** `create_payroll_entries_by_schedule` (ежедневно в 01:00 UTC)

**Файл:** `core/celery/tasks/payroll_tasks.py`

**Логика:**
1. Найти все активные Payment Schedules
2. Для каждого графика проверить, совпадает ли сегодня с днём выплаты (payment_day)
3. Определить период начисления на основе:
   - `frequency` (daily, weekly, biweekly, monthly)
   - `payment_period.start_offset` и `payment_period.end_offset`
4. Найти все объекты с этим графиком (прямая привязка + наследование от подразделений)
5. Для каждого объекта найти активные договоры (Contract.allowed_objects содержит object_id)
6. Для каждого договора:
   - Получить смены за период (с учётом object_id)
   - Рассчитать `hours_worked` и `gross_amount`
   - Создать PayrollEntry с начальными значениями
   - Создать PayrollAdjustment с типом `shift_base` для каждой смены

**Примеры периодов:**
- Weekly (payment_day=2, вторник): start_offset=-22, end_offset=-16 (с прошлого ВТ до понедельника)
- Biweekly: start_offset=-28, end_offset=-14 (две недели)
- Monthly: start_offset=-60, end_offset=-30 (30 дней)

### 2. Автоматические корректировки (Celery)
**Задача:** `process_shift_adjustments()` (ежедневно после завершения смен)

**Логика:**
1. Найти все завершенные смены за вчера
2. Для каждой смены:
   - Проверить опоздание → создать PayrollAdjustment (type=late_start, amount<0)
   - Проверить выполнение обязательных задач → штрафы (type=task_penalty, amount<0)
   - Проверить выполнение необязательных задач → премии (type=task_bonus, amount>0)
3. Привязать корректировки к PayrollEntry (если существует за соответствующий период)

### 3. Ручные корректировки
```python
from shared.services.payroll_adjustment_service import PayrollAdjustmentService

adjustment_service = PayrollAdjustmentService(db)

# Добавить удержание
await adjustment_service.create_manual_adjustment(
    employee_id=14,
    adjustment_type="manual_deduction",
    amount=-100.00,
    description="Штраф за нарушение",
    created_by=owner_id,
    object_id=8,  # опционально
    adjustment_date=date(2025, 10, 15)  # дата начисления, опционально (по умолчанию текущая дата)
)

# Добавить доплату
await adjustment_service.create_manual_adjustment(
    employee_id=14,
    adjustment_type="manual_bonus",
    amount=500.00,
    description="Премия за переработку",
    created_by=owner_id,
    adjustment_date=date(2025, 10, 15)  # дата начисления
)
```

**Редактирование корректировок:**
```python
# Редактирование ручных (manual_*) корректировок
# Поддерживается для применённых и неприменённых корректировок
# При редактировании применённой - автоматически пересчитываются суммы в начислении
await adjustment_service.update_adjustment(
    adjustment_id=123,
    updates={'amount': 150.00, 'description': 'Обновлённое описание'},
    updated_by=owner_id
)
```

**Редактирование/удаление внутри начисления (с автопересчётом):**
- Владелец и управляющий могут редактировать/удалять ручные корректировки прямо на странице начисления
- При изменении суммы корректировки автоматически пересчитываются: `gross_amount`, `total_bonuses`, `total_deductions`, `net_amount`
- Для `manual_deduction` сумма автоматически делается отрицательной при редактировании
- Все изменения записываются в `edit_history` с указанием пользователя, даты и изменённых полей
- История изменений отображается в "Протоколе изменений" на странице начисления

### 4. Запись выплаты
```python
from apps.web.services.payroll_service import PayrollService

payroll_service = PayrollService(db)

# Создать выплату (status=pending)
payment = await payroll_service.create_employee_payment(
    payroll_entry_id=1,
    amount=5000.00,
    payment_date=date.today(),
    payment_method="bank_transfer",
    notes="Перевод на карту",
    created_by_id=owner_id
)

# Подтвердить выплату (pending → completed)
await payroll_service.mark_payment_completed(
    payment_id=payment.id,
    confirmation_code="TXN123456",
    completed_by_id=owner_id
)
```

## Роли и права

### Владелец (Owner)
- ✅ Создание начислений
- ✅ Добавление удержаний/доплат (с указанием даты начисления)
- ✅ Редактирование ручных неприменённых корректировок
- ✅ Одобрение начислений
- ✅ Запись выплат
- ✅ Просмотр всех начислений

### Управляющий (Manager) с правом `can_manage_payroll`
- ✅ Просмотр начислений (по доступным объектам)
- ✅ Добавление удержаний/доплат (с указанием даты начисления)
- ✅ Редактирование ручных неприменённых корректировок (только по доступным объектам)
- ✅ Одобрение начислений (опционально)
- ❌ Запись выплат (только владелец)

### Сотрудник (Employee)
- ✅ Просмотр своих начислений
- ✅ Просмотр истории выплат
- ❌ Изменение данных

## UI страницы и API

### Для владельца
- **GET** `/owner/payroll` - список начислений всех сотрудников
  - Фильтр «Сотрудник»: выпадающий список показывает только сотрудников, чьи договоры пересекаются с выбранным периодом, независимо от текущего статуса договора (учитываются `start_date` и `COALESCE(date(end_date), termination_date)`). Сортировка: `Фамилия Имя`.
  - При пустом выборе сотрудника отображаются начисления для всех сотрудников (включая уволенных), отфильтрованных по договорам владельца.
- **GET** `/owner/payroll/{entry_id}` - детализация с действиями
- **POST** `/owner/payroll/{entry_id}/add-deduction` - добавить удержание
- **POST** `/owner/payroll/{entry_id}/add-bonus` - добавить доплату
- **GET** `/owner/payroll-adjustments` - список всех корректировок (с фильтрами)
  - Query: `adjustment_type` — тип корректировки (shift_base, late_start, task_bonus, task_penalty, manual_bonus, manual_deduction)
  - Query: `employee_id` — ID сотрудника (строка, конвертируется в int)
  - Query: `object_id` — ID объекта (строка, конвертируется в int)
  - Query: `is_applied` — статус применения (all/applied/unapplied)
  - Query: `date_from`, `date_to` — период (YYYY-MM-DD)
  - Query: `page`, `per_page` — пагинация
  - Отбор записей: корректировки, относящиеся к объектам владельца напрямую (`object_id in owner_objects`) или к расписаниям смен (`shift_schedule.object_id in owner_objects`). Привязка к сотрудникам по договорам не обязательна.
- **POST** `/owner/payroll-adjustments/create` - создать ручную корректировку (с полем `adjustment_date`)
- **POST** `/owner/payroll-adjustments/{adjustment_id}/edit` - редактировать ручную корректировку
- **GET** `/owner/payroll-adjustments/{adjustment_id}/history` - история изменений корректировки

**Файлы:**
- `apps/web/routes/payroll.py`
- `apps/web/routes/owner_payroll_adjustments.py`
- `apps/web/templates/owner/payroll_adjustments/list.html`

### Для управляющего (требует `can_manage_payroll`)
- **GET** `/manager/payroll` - список начислений (фильтр по доступным объектам)
- **GET** `/manager/payroll/{entry_id}` - детализация (только просмотр)
- **GET** `/manager/payroll-adjustments` - список корректировок (фильтр по доступным объектам)
- **POST** `/manager/payroll-adjustments/create` - создать ручную корректировку (с полем `adjustment_date`)
- **POST** `/manager/payroll-adjustments/{adjustment_id}/edit` - редактировать ручную корректировку

**Файлы:**
- `apps/web/routes/manager_payroll.py`
- `apps/web/routes/manager_payroll_adjustments.py`
- `apps/web/templates/manager/payroll_adjustments/list.html`

### Для сотрудника
- **GET** `/employee/payroll` - список своих начислений
- **GET** `/employee/payroll/{entry_id}` - детализация с историей выплат

**Файлы:**
- `apps/web/routes/employee_payroll.py`

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
- `idx_payroll_entries_contract_id` - для фильтрации по договору
- `idx_payroll_entries_object_id` - для фильтрации по объекту
- `idx_payroll_adjustments_entry_id` - связь с начислением
- `idx_payroll_adjustments_type` - для фильтрации по типу корректировки
- `idx_employee_payments_entry_id` - связь с начислением
- `idx_employee_payments_status` - для фильтрации по статусу выплаты

## Связи

```
PayrollEntry
├── employee → User
├── contract → Contract
├── object_ → Object
├── created_by → User
├── adjustments → List[PayrollAdjustment]
└── payments → List[EmployeePayment]

PayrollAdjustment
├── payroll_entry → PayrollEntry
├── related_shift → Shift
├── related_task → ShiftTask
└── created_by → User

EmployeePayment
├── payroll_entry → PayrollEntry
├── created_by → User
└── completed_by → User
```

## См. также

- [Системы оплаты](payment_system.md)
- [Графики выплат](payment_schedule.md) (в разработке)
- [Задачи на смену](shift_task.md)
- [Организационная структура](org_structure.md)

