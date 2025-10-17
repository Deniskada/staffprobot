# Роль: Сотрудник (Employee)

## Роуты и эндпоинты
- [GET] `/employee/`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/applications`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/applications/{application_id}`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/applications/{application_id}/interview`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/calendar/data`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/calendar/plan-shift`  — (apps/web/routes/employee.py) — планирование смены для себя
  - Использует `Contract.get_effective_hourly_rate()` для определения ставки
  - Если `contract.use_contract_rate = True`: приоритет ставки договора
  - Если `contract.use_contract_rate = False`: тайм-слот > объект
- [GET] `/employee/api/employees`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/objects`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/shifts/cancel`  — (apps/web/routes/employee.py)
- [GET] `/employee/applications`  — (apps/web/routes/employee.py)
- [GET] `/employee/calendar`  — (apps/web/routes/employee.py)
- [GET] `/employee/calendar/api/objects`  — (apps/web/routes/employee.py)
- [GET] `/employee/earnings`  — (apps/web/routes/employee.py)
- [GET] `/employee/earnings/export`  — (apps/web/routes/employee.py)
- [GET] `/employee/history`  — (apps/web/routes/employee.py)
- [GET] `/employee/objects`  — (apps/web/routes/employee.py)
- [GET] `/employee/profile`  — (apps/web/routes/employee.py)
- [POST] `/employee/profile`  — (apps/web/routes/employee.py)
- [GET] `/employee/reviews`  — (apps/web/routes/employee_reviews.py)
- [GET] `/employee/shifts`  — (apps/web/routes/employee.py)
- [GET] `/employee/shifts/{shift_id}`  — (apps/web/routes/employee.py)
- [GET] `/employee/timeslots/{timeslot_id}`  — (apps/web/routes/employee.py)

## Шаблоны (Jinja2)
- `employee/applications.html`
- `employee/calendar.html`
- `employee/history.html`
- `employee/index.html`
- `employee/objects.html`
- `employee/profile.html`
- `employee/reviews.html`
- `employee/shifts/detail.html`
- `employee/shifts/list.html`
- `employee/timeslots/detail.html`

## Общий календарь (Shared API)
- [GET] `/api/calendar/data`
- [GET] `/api/calendar/timeslots`
- [GET] `/api/calendar/shifts`
- [GET] `/api/calendar/stats`
- [GET] `/api/calendar/objects`

## Начисления и выплаты (Payroll) — Итерация 23
- [GET] `/employee/payroll` — список своих начислений за периоды
  - Query: `period_start` — начало периода (YYYY-MM-DD)
  - Query: `period_end` — конец периода (YYYY-MM-DD)
  - Показывает начисления, удержания, доплаты
- [GET] `/employee/payroll/{entry_id}` — детализация начисления
  - Список смен за период
  - Автоматические удержания (опоздание, задачи)
  - Автоматические премии (выполненные задачи)
  - Ручные корректировки от владельца/управляющего
  - История выплат
