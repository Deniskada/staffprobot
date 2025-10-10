# Сущности (Entities)

Документация моделей данных системы StaffProBot.

## Основные сущности

### Пользователи и договоры
- [Сотрудники (Employees)](employees.md) — модель User, регистрация, профили
- [Договоры (Contracts)](contract.md) — условия работы, ставки, системы оплаты, права

### Объекты и график
- [Объекты (Objects)](objects.md) — рабочие места/локации
- [Тайм-слоты (Timeslots)](timeslots.md) — запланированные интервалы работы
- [Смены (Shifts)](shifts.md) — фактически отработанные смены
- [Задачи на смену (Shift Tasks)](shift_task.md) — обязательные и необязательные задачи

### Организационная структура (Итерация 23)
- [Подразделения (Org Structure)](org_structure.md) — иерархическая структура компании

### Финансы и оплата (Итерация 23)
- [Системы оплаты (Payment Systems)](payment_system.md) — простая, окладная, премиальная
- [Начисления и выплаты (Payroll)](payroll.md) — расчет зарплат, удержания, премии

### Отзывы и заявки
- [Отзывы (Reviews)](reviews.md) — отзывы сотрудников на объекты
- [Заявки (Applications)](applications.md) — заявки на работу от сотрудников

### Аналитика
- [Отчеты (Reports)](reports.md) — статистика и экспорт данных

### Тарифы и лимиты
- [Тарифы и лимиты (Limits & Tariffs)](limits_tariffs.md) — ограничения по тарифам

## Связи между сущностями

```
User (Owner)
├── OrgStructureUnit (подразделения)
│   ├── payment_system_id → PaymentSystem
│   ├── payment_schedule_id → PaymentSchedule
│   └── late_settings (наследуемые)
│
├── Object (объекты)
│   ├── org_unit_id → OrgStructureUnit
│   ├── payment_system_id → PaymentSystem (optional)
│   ├── shift_tasks (JSONB)
│   └── late_settings (optional)
│
├── Contract (договоры)
│   ├── employee_id → User
│   ├── use_contract_rate (Boolean)
│   ├── payment_system_id → PaymentSystem
│   └── manager_permissions (JSON)
│
├── Timeslot (тайм-слоты)
│   ├── object_id → Object
│   ├── employee_id → User
│   └── timeslot_task_templates (шаблоны задач)
│
├── Shift (смены)
│   ├── object_id → Object
│   ├── employee_id → User
│   ├── shift_tasks → List[ShiftTask]
│   └── hourly_rate (calculated)
│
├── PayrollEntry (начисления)
│   ├── employee_id → User
│   ├── deductions → List[PayrollDeduction]
│   ├── bonuses → List[PayrollBonus]
│   └── payments → List[EmployeePayment]
│
└── Application (заявки)
    ├── employee_id → User
    └── object_id → Object
```

## Индексы и производительность

Все основные таблицы имеют индексы на:
- Foreign keys
- Поля для фильтрации (status, is_active, level)
- Поля для поиска (owner_id, employee_id, object_id)
- Даты (start_date, end_date, period_start, period_end)

## См. также

- [Роль: Владелец](../roles/owner.md)
- [Роль: Управляющий](../roles/manager.md)
- [Роль: Сотрудник](../roles/employee.md)

