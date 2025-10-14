# Роль: Управляющий (Manager)

## Роуты и эндпоинты
- [GET] `/`  — (apps/web/routes/manager.py) — редирект на /manager/dashboard
- [GET] `/`  — (apps/web/routes/manager.py) — редирект на /manager/dashboard
- [POST] `/api/applications/approve`  — (apps/web/routes/manager.py)
- [GET] `/api/applications/count`  — (apps/web/routes/manager.py)
- [POST] `/api/applications/finalize-contract`  — (apps/web/routes/manager.py)
- [POST] `/api/applications/reject`  — (apps/web/routes/manager.py)
- [GET] `/api/applications/{application_id}`  — (apps/web/routes/manager.py)
- [POST] `/api/calendar/check-availability`  — (apps/web/routes/manager.py)
- [POST] `/api/calendar/plan-shift`  — (apps/web/routes/manager.py)
- [GET] `/api/employees`  — (apps/web/routes/manager.py)
- [GET] `/api/employees/for-object/{object_id}`  — (apps/web/routes/manager.py)
- [GET] `/applications`  — (apps/web/routes/manager.py)
- [GET] `/calendar`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/data`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/employees`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/objects`  — (apps/web/routes/manager.py)
- [POST] `/calendar/api/quick-create-timeslot`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/timeslot/{timeslot_id}`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/timeslots-status`  — (apps/web/routes/manager.py)
- [GET] `/dashboard`  — (apps/web/routes/manager.py)
- [GET] `/employees`  — (apps/web/routes/manager.py)
- [GET] `/employees/add`  — (apps/web/routes/manager.py)
- [POST] `/employees/add`  — (apps/web/routes/manager.py)
- [GET] `/employees/{employee_id}`  — (apps/web/routes/manager.py) — детали сотрудника с проверкой прав can_manage_employees для каждого договора
- [GET] `/contracts/{contract_id}/view`  — (apps/web/routes/manager.py) — просмотр договора (доступен если у управляющего есть доступ к хотя бы одному объекту из allowed_objects)
- [GET] `/contracts/{contract_id}/edit`  — (apps/web/routes/manager.py) — редактирование договора (требует can_manage_employees на одном из объектов договора)
- [POST] `/contracts/{contract_id}/edit`  — (apps/web/routes/manager.py) — сохранение изменений договора (требует can_manage_employees)
- [POST] `/contracts/{contract_id}/terminate`  — (apps/web/routes/manager.py) — расторжение договора (требует can_manage_employees)
- [GET] `/employees/{employee_id}/edit`  — (apps/web/routes/manager.py) — форма редактирования сотрудника (только профиль)
- [POST] `/employees/{employee_id}/edit`  — (apps/web/routes/manager.py)
- [GET] `/employees/{employee_id}/shifts`  — (apps/web/routes/manager.py)
- [POST] `/employees/{employee_id}/terminate`  — (apps/web/routes/manager.py) — устаревший метод (DEPRECATED, используйте /contracts/{contract_id}/terminate)
- [GET] `/manager/reviews-simple`  — (apps/web/routes/manager_reviews_simple.py)
- [GET] `/manager/timeslots`  — (apps/web/routes/manager_timeslots.py)
- [POST] `/manager/timeslots/bulk-delete`  — (apps/web/routes/manager_timeslots.py)
- [POST] `/manager/timeslots/bulk-edit`  — (apps/web/routes/manager_timeslots.py)
- [GET] `/manager/timeslots/object/{object_id}`  — (apps/web/routes/manager_timeslots.py)
- [GET] `/manager/timeslots/object/{object_id}/create`  — (apps/web/routes/manager_timeslots.py)
- [POST] `/manager/timeslots/object/{object_id}/create`  — (apps/web/routes/manager_timeslots.py)
- [GET] `/manager/timeslots/{timeslot_id}/edit`  — (apps/web/routes/manager_timeslots.py)
- [POST] `/manager/timeslots/{timeslot_id}/edit`  — (apps/web/routes/manager_timeslots.py)
- [GET] `/objects`  — (apps/web/routes/manager.py)
- [GET] `/objects/{object_id}`  — (apps/web/routes/manager.py)
- [GET] `/objects/{object_id}/edit`  — (apps/web/routes/manager.py)
- [POST] `/objects/{object_id}/edit`  — (apps/web/routes/manager.py)
- [GET] `/profile`  — (apps/web/routes/manager.py)
- [POST] `/profile`  — (apps/web/routes/manager.py)
- [GET] `/reports`  — (apps/web/routes/manager.py)
- [POST] `/reports/generate`  — (apps/web/routes/manager.py)
- [GET] `/reports/stats/period`  — (apps/web/routes/manager.py)
- [GET] `/reviews`  — (apps/web/routes/manager_reviews.py)
- [GET] `/shifts`  — (apps/web/routes/manager.py)
- [GET] `/shifts/{shift_id}`  — (apps/web/routes/manager.py)
- [POST] `/shifts/{shift_id}/cancel`  — (apps/web/routes/manager.py)
- [GET] `/timeslots/{timeslot_id}`  — (apps/web/routes/manager.py)
- [POST] `/timeslots/{timeslot_id}/edit`  — (apps/web/routes/manager.py) — форма: form-data; ответ: 303 Redirect на `/manager/timeslots/object/{object_id}` — причина изменения: ранее ожидался JSON, теперь корректно обрабатывается форма.

## Шаблоны (Jinja2)
- `manager/applications.html`
- `manager/calendar.html`
- `manager/dashboard.html`
- `manager/employees.html`
- `manager/employees/add.html`
- `manager/employees/detail.html` — детальная информация о сотруднике с таблицей договоров (кнопки Просмотр/Редактировать/Расторгнуть с проверкой прав)
- `manager/employees/edit.html` — редактирование профиля сотрудника
- `manager/employees/shifts.html`
- `manager/contracts/view.html` — просмотр договора (read-only, доступен всем управляющим с доступом к объектам)
- `manager/contracts/edit.html` — редактирование договора (только с can_manage_employees)
- `manager/objects.html`
- `manager/objects/detail.html`
- `manager/objects/edit.html`
- `manager/profile.html`
- `manager/reports/index.html`
- `manager/reviews.html`
- `manager/shifts/detail.html`
- `manager/shifts/list.html`

## Общий календарь (Shared API)
- [GET] `/api/calendar/data`
- [GET] `/api/calendar/timeslots`
- [GET] `/api/calendar/shifts`
- [GET] `/api/calendar/stats`
- [GET] `/api/calendar/objects`

## Начисления и выплаты (Payroll) — Итерация 23
**Требуется право:** `manager_permissions.can_manage_payroll = true`

- [GET] `/manager/payroll` — (apps/web/routes/manager_payroll.py) — список начислений сотрудников
  - Query: `period_start` — начало периода (YYYY-MM-DD)
  - Query: `period_end` — конец периода (YYYY-MM-DD)
  - Query: `object_id` — фильтр по объекту (только доступные)
  - Показываются только сотрудники, работающие на доступных управляющему объектах
- [GET] `/manager/payroll/{entry_id}` — детализация начисления
  - Смены за период (только по доступным объектам)
  - Удержания и доплаты (автоматические и ручные)
  - **Примечание:** Управляющий НЕ может одобрить или записать выплату (только владелец)
