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
- [GET] `/api/employees/for-object/{object_id}`  — (apps/web/routes/manager.py) — возвращает сгруппированный список сотрудников (`{"active": [...], "former": [...]}`) для выпадающих списков (инциденты, планировщик)
- [GET] `/applications`  — (apps/web/routes/manager.py)
- [GET] `/calendar`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/data`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/employees`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/objects`  — (apps/web/routes/manager.py)
- [POST] `/calendar/api/quick-create-timeslot`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/timeslot/{timeslot_id}`  — (apps/web/routes/manager.py)
- [GET] `/calendar/api/timeslots-status`  — (apps/web/routes/manager.py)
- [GET] `/dashboard`  — (apps/web/routes/manager.py) — дашборд управляющего с кликабельными карточками статистики (Объекты, Активные смены, Сотрудники, Запланированные на сегодня), счетчик запланированных смен на сегодня из ShiftSchedule, подсчет сотрудников только с активными договорами у владельцев, с которыми есть активный контракт у управляющего
- [GET] `/employees`  — (apps/web/routes/manager.py) — список сотрудников с фильтрацией по ФИО, сортировкой (name, phone, created_at) и пагинацией (25, 50, 100), отображение "Фамилия Имя"
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
- [GET] `/objects`  — (apps/web/routes/manager.py) — список объектов с фильтрацией по названию и адресу, сортировкой (name, address, hourly_rate, opening_time, closing_time, is_active, created_at) и пагинацией (25, 50, 100)
- [GET] `/objects/{object_id}`  — (apps/web/routes/manager.py)
- [GET] `/objects/{object_id}/edit`  — (apps/web/routes/manager.py)
- [POST] `/objects/{object_id}/edit`  — (apps/web/routes/manager.py)
- [GET] `/profile`  — (apps/web/routes/manager.py)
- [POST] `/profile`  — (apps/web/routes/manager.py)
- [GET] `/profiles`  — (apps/web/routes/manager_profiles.py) — мастер «Мои профили» (shared wizard, query: profile_id)
- [GET] `/reports`  — (apps/web/routes/manager.py)
- [POST] `/reports/generate`  — (apps/web/routes/manager.py)
- [GET] `/reports/stats/period`  — (apps/web/routes/manager.py)
- [GET] `/reviews`  — (apps/web/routes/manager_reviews.py)
- [GET] `/shifts`  — (apps/web/routes/manager.py)
- [GET] `/shifts/{shift_id}`  — (apps/web/routes/manager.py)
- [POST] `/shifts/{shift_id}/cancel`  — (apps/web/routes/manager.py)
- [GET] `/support`  — (apps/web/routes/support.py) — центр поддержки (хаб поддержки)
- [GET] `/support/bug`  — (apps/web/routes/support.py) — форма подачи бага
- [GET] `/support/faq`  — (apps/web/routes/support.py) — FAQ база знаний
- [GET] `/support/my-bugs`  — (apps/web/routes/support.py) — список моих багов
- [GET] `/timeslots/{timeslot_id}`  — (apps/web/routes/manager.py)
- [POST] `/timeslots/{timeslot_id}/edit`  — (apps/web/routes/manager.py) — форма: form-data; ответ: 303 Redirect на `/manager/timeslots/object/{object_id}` — причина изменения: ранее ожидался JSON, теперь корректно обрабатывается форма.

### Инциденты
- [GET] `/manager/incidents` — список инцидентов (фильтры по объекту/статусу, сортировка, пагинация)
- [GET] `/manager/incidents/create` — форма создания инцидента
- [POST] `/manager/incidents/create` — создание инцидента (автоудержание по ущербу)
- [GET] `/manager/incidents/{id}/edit` — редактирование инцидента и история изменений
- [POST] `/manager/incidents/{id}/edit` — сохранение изменений, перераспределение удержаний/доплат
- После фикса 18.11.2025 форма редактирования отображает таблицу связанных корректировок и при смене даты инцидента переносит дату только корректировкам текущего сотрудника (если корректировка была применена — возвращается в статус «не применена»).
- [POST] `/manager/incidents/{id}/status` — смена статуса (через `IncidentService`)
- [GET] `/manager/incidents/api/categories` — категории владельца для выбранного объекта
- **UI:** выбор сотрудника заблокирован до выбора объекта; выпадающий список строится из `EmployeeSelectorService.get_employees_for_object` — активные сотрудники идут первыми (алфавитно), затем разделитель «Бывшие» (жирный курсив) и архивные сотрудники (курсив).

## Шаблоны (Jinja2)
- `manager/applications.html`
- `manager/calendar.html`
  - Загружает текущий месяц, скролл подгружает следующий (`universal_calendar.js`)
  - Клик по тайм-слоту → общая модалка `plan_shift_modal.js`; по запланированной смене → `/manager/shifts/plan` с `employee_id`, `object_id`, `return_to`
  - Фильтры (`object_id`) сохраняются при возврате из планировщика
- `manager/shifts/plan.html` — страница планирования смен управляющего
  - UI идентичен владельцу: свободные интервалы по всем трекам и список «Запланированные смены»
  - `preselectedEmployeeId` подставляется при переходе из календаря
  - В одной форме можно отменить существующие смены и создать новые (очистка кэша календаря после операции)
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
- `manager/payroll/list.html` — интерфейс начислений с двумя вкладками. По умолчанию открывается «Сводка по сотрудникам» (агрегированные показатели по каждому сотруднику, сортировка по ФИО/количеству/сумме/последнему периоду, фильтры по периоду и объекту, переключатель «Показать уволенных сотрудников»). Вкладка «Начисления» показывает плоский список записей.
- `manager/payroll/detail.html` — детализация начислений сотрудника: верхняя таблица с начислениями (сортировка по столбцам) и подробный блок ниже. Раздел «Выплаты» отображается перед протоколом изменений. Кнопки добавления удержаний/доплат активны только пока нет выплат.
- `manager/payroll_adjustments/list.html` — список начислений (PayrollAdjustment) с фильтрами и кнопкой создания (требует can_manage_payroll)
- `manager/profile.html` — страница профиля с блоком «Мои профили» (таблица с кнопками редактирования/удаления, ссылка на мастер)
- `manager/profile/profiles.html` — мастер «Мои профили» (include shared/profiles_wizard.html, manager_extra_js: Yandex Maps, address_map.js, profiles_wizard.js)
- `manager/reports/index.html`
- `manager/reviews.html`
- `manager/shifts/detail.html`
- `manager/shifts/list.html`
- `support/hub.html` — центр поддержки (использует base_template для роли, блок manager_content)
- `support/bug.html` — форма подачи бага (использует base_template для роли, блок manager_content)
- `support/faq.html` — FAQ база знаний (использует base_template для роли, блок manager_content)
- `support/my_bugs.html` — список моих багов (использует base_template для роли, блок manager_content)

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

- [GET] `/manager/payroll` — (apps/web/routes/manager_payroll.py) — сводный список начислений
  - View: вкладка «Сводка по сотрудникам» (агрегирует количество начислений, суммарную выплату, последний период) и вкладка «Начисления» (плоский список записей).
  - Query: `period_start`, `period_end` — границы периода (YYYY-MM-DD), по умолчанию последние 60 дней.
  - Query: `object_id` — фильтр по объекту (строка, безопасно конвертируется в Optional[int]).
  - Query: `show_inactive=true|false` — включает сотрудников с завершёнными договорами. В сводке они помечаются бейджем «Уволен».
  - Доступ проверяется через `ManagerPermissionService`: учитываются активные и архивные договоры по объектам, к которым есть доступ.
  - Сортировка: ФИО, количество начислений, суммарная сумма, последний период. Пагинация 25/50/100 записей.
- [GET] `/manager/payroll/{entry_id}` — (apps/web/routes/manager_payroll.py) — детализация начисления сотрудника
  - Страница загружается по `entry_id`, но верхняя таблица содержит все начисления сотрудника; выбор строки обновляет подробный блок.
  - Детальный блок содержит состав начисления, корректировки, выплаты (размещены перед протоколом изменений) и историю изменений.
  - Доступ проверяется через `ManagerPermissionService.get_user_accessible_employee_ids(include_inactive=True)`.
  - Управляющий не может подтверждать выплаты, но видит их статус и детали; добавление корректировок доступно пока нет зафиксированных выплат.
- [GET] `/manager/payroll/statement/{employee_id}` — (apps/web/routes/manager_payroll.py) — расчётный лист по сотруднику (ограничение по доступным объектам)
  - Использует общий `PayrollStatementService`: создаёт недостающие начисления по графику выплат, объединяет корректировки/выплаты/баланс.
  - UI совпадает с owner-версией: кнопки «Печать» и «Экспорт», карточки суммарных показателей, блоки по периодам.
- [GET] `/manager/payroll/statement/{employee_id}/export` — Excel расчётного листа (общий helper `build_statement_workbook`)

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
  - Form: `employee_id`, `adjustment_type`, `amount`, `description`, `adjustment_date` (дата начисления), `object_id` (опц), `shift_id` (опц)
  - Проверка доступа к объекту (если указан)
  - Только типы: manual_bonus, manual_deduction
  - **Важно:** `adjustment_date` устанавливает `created_at` корректировки на указанную дату
- [POST] `/manager/payroll-adjustments/{adjustment_id}/edit` — (apps/web/routes/manager_payroll_adjustments.py) — редактировать ручную корректировку
  - Form: `amount`, `description`
  - Только ручные неприменённые корректировки по доступным объектам

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
