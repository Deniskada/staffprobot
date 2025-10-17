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
- [POST] `/api/calendar/plan-shift`  — (apps/web/routes/manager.py) — планирование смены
  - Приоритет ставки: входное значение > `Contract.get_effective_hourly_rate()`
  - Если `contract.use_contract_rate = True`: приоритет ставки договора
  - Если `contract.use_contract_rate = False`: тайм-слот > объект
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
- `manager/payroll/list.html` — список выплат (PayrollEntry) с фильтрами (требует can_manage_payroll)
- `manager/payroll/detail.html` — детализация выплаты (требует can_manage_payroll)
- `manager/payroll_adjustments/list.html` — список начислений (PayrollAdjustment) с фильтрами и кнопкой создания (требует can_manage_payroll)
- `manager/profile.html`
- `manager/reports/index.html`
- `manager/reviews.html`
- `manager/shifts/detail.html`
- `manager/shifts/list.html`

## Контекст управляющего (Manager Context)

Функция `get_manager_context(user_id, session)` в `apps/web/routes/manager.py` формирует общий контекст для всех страниц управляющего:

- `available_interfaces` — список доступных интерфейсов для переключения ролей
- `new_applications_count` — количество новых заявок
- `can_manage_payroll` — право на управление начислениями и выплатами
  - Определяется из `contract.manager_permissions.can_manage_payroll` (JSON поле)
  - Управляющий должен иметь хотя бы один активный договор с этим правом
  - Контролирует видимость пунктов меню "Выплаты" и "Начисления"

**Важно:** Все роуты управляющего должны передавать `**manager_context` в шаблон для корректного отображения меню.

## Общий календарь (Shared API)
- [GET] `/api/calendar/data`
- [GET] `/api/calendar/timeslots`
- [GET] `/api/calendar/shifts`
- [GET] `/api/calendar/stats`
- [GET] `/api/calendar/objects`

## Выплаты (Payroll Entries) — Итерация 23
**Требуется право:** `manager_permissions.can_manage_payroll = true`
**Меню:** "Выплаты"

- [GET] `/manager/payroll` — (apps/web/routes/manager_payroll.py) — список выплат сотрудников (PayrollEntry)
  - Query: `period_start` — начало периода (YYYY-MM-DD)
  - Query: `period_end` — конец периода (YYYY-MM-DD), по умолчанию: последние 60 дней
  - Query: `object_id` — фильтр по объекту (строка, конвертируется в int для обработки пустых значений)
  - Фильтрация: только PayrollEntry по доступным объектам управляющего
  - Показываются только сотрудники, работающие на доступных объектах
- [GET] `/manager/payroll/{entry_id}` — (apps/web/routes/manager_payroll.py) — детализация выплаты
  - Смены за период (только по доступным объектам)
  - Корректировки (adjustments)
  - Выплаты (payments)
  - **Примечание:** Управляющий НЕ может одобрить или записать выплату (только владелец)

## Начисления (Payroll Adjustments) — Итерация 23
**Требуется право:** `manager_permissions.can_manage_payroll = true`
**Меню:** "Начисления"

- [GET] `/manager/payroll-adjustments` — (apps/web/routes/manager_payroll_adjustments.py) — список корректировок с фильтрами
  - Query: `adjustment_type` — тип (shift_base, late_start, task_bonus, task_penalty, manual_bonus, manual_deduction)
  - Query: `employee_id` — ID сотрудника (строка, конвертируется в int)
  - Query: `object_id` — ID объекта (строка, конвертируется в int)
  - Query: `is_applied` — статус (all/applied/unapplied)
  - Query: `date_from`, `date_to` — период (YYYY-MM-DD), по умолчанию: последние 60 дней
  - Query: `page`, `per_page` — пагинация
  - Фильтрация: PayrollAdjustment по доступным объектам ИЛИ без объекта (NULL)
  - Показываются сотрудники с allowed_objects, пересекающимися с доступными объектами
- [POST] `/manager/payroll-adjustments/create` — (apps/web/routes/manager_payroll_adjustments.py) — создать ручную корректировку
  - Form: `employee_id`, `adjustment_type`, `amount`, `description`, `object_id` (опционально), `shift_id` (опционально)
  - Проверка доступа к объекту (если указан)
  - Только типы: manual_bonus, manual_deduction

## Защита от самоуправления и безопасность

### Ограничения для управляющего:

**1. Список сотрудников (`/manager/employees`):**
- Управляющий НЕ видит себя в списке (фильтр `User.id != user_id`)
- Показываются только сотрудники с активными договорами на доступных объектах

**2. Детали сотрудника (`/manager/employees/{employee_id}`):**
- Запрещен доступ к своей странице (`employee_id == user_id`)
- Ошибка 403: "Вы не можете управлять своими договорами через этот интерфейс"

**3. Редактирование договора (все методы):**
- Проверка `contract.employee_id != user_id` во всех роутах редактирования
- Управляющий НЕ может редактировать свои договоры

**4. Расторжение договора (все методы):**
- Проверка `employee_id != user_id` или `contract.employee_id != user_id`
- Управляющий НЕ может расторгать свои договоры
- При расторжении последнего договора: `user.is_active = false`

**5. Создание договора (`/manager/employees/add`):**
- `owner_id` определяется из **выбранных** объектов, а не первого доступного
- Проверка, что все выбранные объекты принадлежат одному владельцу
