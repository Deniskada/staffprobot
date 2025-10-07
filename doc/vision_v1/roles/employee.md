# Роль: Сотрудник (Employee)

## Роуты и эндпоинты
- [GET] `/employee/`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/applications`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/applications/{application_id}`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/applications/{application_id}/interview`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/calendar/data`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/calendar/plan-shift`  — (apps/web/routes/employee.py)
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
