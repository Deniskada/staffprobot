# Договоры (Contracts)

## Описание

Договоры между владельцем и сотрудниками/управляющими. Определяют условия работы, права доступа, систему оплаты и почасовую ставку.

## Модель данных

**Таблица:** `contracts`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `contract_number` | String(100) | Номер договора (уникальный) |
| `owner_id` | Integer | FK → users.id (владелец) |
| `employee_id` | Integer | FK → users.id (сотрудник) |
| `template_id` | Integer | FK → contract_templates.id |
| `title` | String(255) | Название договора |
| `content` | Text | Текст договора |
| `hourly_rate` | Numeric(10,2) | Почасовая ставка (₽) |
| **`use_contract_rate`** | Boolean | **Приоритет ставки из договора** |
| **`payment_system_id`** | Integer | **FK → payment_systems.id** |
| `payment_schedule_id` | Integer | FK → payment_schedules.id |
| `start_date` | Date | Дата начала |
| `end_date` | Date | Дата окончания |
| `status` | String(20) | draft / active / terminated |
| `is_active` | Boolean | Активность |
| `allowed_objects` | JSON | Список ID доступных объектов |
| **`is_manager`** | Boolean | **Является ли управляющим** |
| **`manager_permissions`** | JSON | **Права управляющего** |
| `values` | JSON | Динамические значения полей |
| `created_at` | DateTime | Дата создания |
| `updated_at` | DateTime | Дата обновления |
| `signed_at` | DateTime | Дата подписания |
| `terminated_at` | DateTime | Дата расторжения |

## Новые поля (Итерация 23)

### 1. `use_contract_rate` (Boolean)
**Назначение:** Указывает, что ставка из договора имеет приоритет над ставками тайм-слота и объекта.

**Логика:**
```python
if contract.use_contract_rate and contract.hourly_rate:
    hourly_rate = contract.hourly_rate  # Высший приоритет!
elif timeslot.hourly_rate:
    hourly_rate = timeslot.hourly_rate
else:
    hourly_rate = object.hourly_rate
```

**UI:** Чекбокс "Приоритет ставки из договора" в формах создания/редактирования договора.

### 2. `payment_system_id` (FK)
**Назначение:** Определяет систему оплаты для расчета зарплаты сотрудника.

**Значения:**
- `1` - Простая повременная
- `2` - Окладная
- `3` - Повременно-премиальная

**Влияние:** Определяет, применяются ли автоматические штрафы/премии за задачи.

**UI:** Dropdown "Система оплаты труда" в формах договора.

### 3. `manager_permissions.can_manage_payroll` (JSON → Boolean)
**Назначение:** Право управляющего на работу с начислениями и выплатами.

**Структура manager_permissions:**
```json
{
  "can_view": true,
  "can_edit": true,
  "can_delete": false,
  "can_manage_employees": true,
  "can_manage_payroll": true,  // Новое поле!
  "can_view_finances": true,
  "can_edit_rates": false
}
```

**Проверка прав:**
```python
from apps.web.dependencies import require_manager_payroll_permission

@router.get("/manager/payroll")
async def manager_payroll(current_user = Depends(require_manager_payroll_permission)):
    # Доступ только если can_manage_payroll = true
    ...
```

**UI:** Чекбокс "Управление начислениями и выплатами" в секции "Права управляющего".

## Типы договоров

### Договор сотрудника
- `is_manager = False`
- `manager_permissions = None`
- Определяет условия работы и систему оплаты

### Договор управляющего
- `is_manager = True`
- `manager_permissions = {...}` - набор прав
- `allowed_objects` - список доступных объектов

## Жизненный цикл

### 1. Создание (draft)
```python
contract = Contract(
    owner_id=7,
    employee_id=14,
    hourly_rate=500.00,
    use_contract_rate=True,
    payment_system_id=3,  # Повременно-премиальная
    status="draft"
)
```

### 2. Активация (draft → active)
После подписания сотрудником:
```python
contract.status = "active"
contract.signed_at = datetime.now()
```

### 3. Расторжение (active → terminated)
```python
contract.status = "terminated"
contract.terminated_at = datetime.now()
contract.is_active = False
```

## Приоритет ставок

### Логика в методе `get_effective_hourly_rate()`
```python
def get_effective_hourly_rate(
    self,
    timeslot_rate: Optional[float] = None,
    object_rate: Optional[float] = None
) -> float:
    """
    1. Если use_contract_rate=True и hourly_rate указана → contract.hourly_rate
    2. Иначе, если timeslot_rate указана → timeslot_rate
    3. Иначе → object_rate
    """
    if self.use_contract_rate and self.hourly_rate:
        return float(self.hourly_rate)
    
    if timeslot_rate is not None:
        return timeslot_rate
    
    return object_rate if object_rate else 0.0
```

## UI

### Форма создания договора
**Путь:** `/owner/employees/create`

**Новые поля:**
- Чекбокс "Приоритет ставки из договора" (`use_contract_rate`)
- Dropdown "Система оплаты труда" (`payment_system_id`)

### Форма редактирования договора
**Путь:** `/owner/employees/contract/{contract_id}/edit`

**Новые поля:**
- Чекбокс "Приоритет ставки из договора"
- Dropdown "Система оплаты труда"
- Чекбокс "Управление начислениями и выплатами" (для управляющих)

### Детализация договора
**Путь:** `/owner/employees/{employee_id}`

**Отображение:**
- Статус приоритета ставки (✅ / ❌)
- Название системы оплаты
- Список прав управляющего (если `is_manager=True`)

## Индексы

- `idx_contracts_owner_id` - для поиска по владельцу
- `idx_contracts_employee_id` - для поиска по сотруднику
- `idx_contracts_status` - для фильтрации по статусу
- `idx_contracts_is_active` - для фильтрации активных
- `idx_contracts_payment_system_id` - для группировки по системе оплаты

## Связи

```
Contract
├── owner → User
├── employee → User
├── template → ContractTemplate
├── payment_system → PaymentSystem
└── payment_schedule → PaymentSchedule
```

## Валидация

### При создании/редактировании
- `hourly_rate` >= 0 (в рублях, Numeric)
- `payment_system_id` должен существовать в `payment_systems`
- Если `use_contract_rate=True`, то `hourly_rate` обязательна
- Для управляющих: `allowed_objects` не должен быть пустым

### Уникальность
- `contract_number` - уникален в рамках владельца

## См. также

- [Системы оплаты](payment_system.md)
- [Начисления и выплаты](payroll.md)
- [Сотрудники](employees.md)

