# Роль: Владелец (Owner)

## Роуты и эндпоинты
- [GET] `/owner/`  — (apps/web/routes/owner.py)
- [GET] `/owner/`  — (apps/web/routes/owner_shifts.py)
- [GET] `/owner/`  — (apps/web/routes/limits.py)
- [GET] `/owner/admin/api/overview`  — (apps/web/routes/limits.py)
- [GET] `/owner/admin/overview`  — (apps/web/routes/limits.py)
- [POST] `/owner/api/applications/approve`  — (apps/web/routes/owner.py)
- [GET] `/owner/api/applications/count`  — (apps/web/routes/owner.py)
- [POST] `/owner/api/applications/finalize-contract`  — (apps/web/routes/owner.py)
- [POST] `/owner/api/applications/reject`  — (apps/web/routes/owner.py)
- [GET] `/owner/api/applications/{application_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/api/calendar/check-availability`  — (apps/web/routes/owner.py)
- [POST] `/owner/api/calendar/plan-shift`  — (apps/web/routes/owner.py) — планирование смены через drag&drop
  - Использует `Contract.get_effective_hourly_rate()` для определения ставки
  - Если `contract.use_contract_rate = True`: приоритет ставки договора
  - Если `contract.use_contract_rate = False`: тайм-слот > объект
- [GET] `/owner/api/check/employee`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/check/feature/{feature}`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/check/manager`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/check/object`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/contracts/my-contracts`  — (apps/web/routes/owner.py)
- [GET] `/owner/api/employees`  — (apps/web/routes/owner.py)
- [GET] `/owner/incidents/api/employees?object_id={id}` — (apps/web/routes/owner_incidents.py) — возвращает сгруппированный список сотрудников объекта (`active`, затем `former`), используется в формах инцидентов
  
### Инциденты
- [GET] `/owner/incidents` — список инцидентов (apps/web/routes/owner_incidents.py)
- [POST] `/owner/incidents/create` — создать инцидент (необязательные поля: Номер, Дата, Объект, Сотрудник, Ущерб)
- [GET] `/owner/incidents/{id}/edit` — форма редактирования, смена статуса, история изменений
- [POST] `/owner/incidents/{id}/edit` — сохранить изменения
- [POST] `/owner/incidents/{id}/status` — смена статуса (учитываются автокорректировки)
- [GET] `/owner/incidents/categories` — пользовательские категории владельца
- [POST] `/owner/incidents/categories` — создать/деактивировать категорию
- [GET] `/owner/incidents/reports` — отчеты по инцидентам
  - Форма редактирования отображает таблицу всех корректировок, привязанных к инциденту; при изменении даты инцидента обновляются даты только корректировок текущего сотрудника, а применённые корректировки возвращаются в статус «не применена», чтобы попасть в новый расчёт.
  - Фильтрация: Contract.owner_id == user_id AND allowed_objects @> [object_id]
  - Используется в модальном окне планирования смен на /owner/shifts
  - **UI:** выбор сотрудника блокируется до выбора объекта; после загрузки показываются активные сотрудники (алфавитно), затем разделитель «Бывшие» (жирный курсив) и архивные сотрудники (курсив). Данные предоставляет `EmployeeSelectorService.get_employees_for_owner`.
- [GET] `/owner/api/summary`  — (apps/web/routes/limits.py)
- [GET] `/owner/applications`  — (apps/web/routes/owner.py)
- [POST] `/owner/bulk-delete`  — (apps/web/routes/owner_timeslots.py)
- [GET] `/owner/calendar`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/analysis`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/analysis/chart-data`  — (apps/web/routes/owner.py)
- [POST] `/owner/calendar/analysis/fill-gaps/{object_id}`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/api/data`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/api/objects`  — (apps/web/routes/owner.py)
- [POST] `/owner/calendar/api/quick-create-timeslot`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/api/timeslot/{timeslot_id}`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/api/timeslots-status`  — (apps/web/routes/owner.py)
- [GET] `/owner/calendar/week`  — (apps/web/routes/owner.py)
- [GET] `/owner/dashboard`  — (apps/web/routes/owner.py) — главная страница владельца
  - Быстрые действия:
    - "Добавить сотрудника" → `/owner/employees/create`
    - "Запланировать смену" → `/owner/shifts?action=plan` (автоматически открывает модальное окно)
    - "Календарь" → `/owner/calendar`
- [GET] `/owner/employees`  — (apps/web/routes/owner.py) — список сотрудников
  - Query: `view_mode=cards|list` (default: list)
  - Query: `sort_by=employee|telegram_id|status` (default: employee)
  - Query: `sort_order=asc|desc` (default: asc)
  - Query: `q_employee` (фильтр по Фамилия Имя; ищется обе комбинации)
  - Query: `q_telegram` (фильтр по Telegram ID)
  - Query: `q_status=active|former` (фильтр по статусу, активный определяется по активным договорам)
- [GET] `/owner/employees/contract/{contract_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/employees/contract/{contract_id}/activate`  — (apps/web/routes/owner.py)
- [GET] `/owner/employees/contract/{contract_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/employees/contract/{contract_id}/edit`  — (apps/web/routes/owner.py)
- [GET] `/owner/employees/contract/{contract_id}/pdf`  — (apps/web/routes/owner.py)
- [POST] `/owner/employees/contract/{contract_id}/terminate`  — (apps/web/routes/owner.py)
- [GET] `/owner/employees/create`  — (apps/web/routes/owner.py)
- [POST] `/owner/employees/create`  — (apps/web/routes/owner.py)
  - Form: `employee_telegram_id`, `first_name`, `last_name`, `phone`, `email`, `birth_date` (поля профиля), `title`, `content`, `hourly_rate`, `start_date`, `end_date`, `template_id`, `allowed_objects`, `is_manager`, `manager_permissions` (поля договора)
  - **Важно:** Поля профиля (`first_name`, `last_name`, `phone`, `email`, `birth_date`) сохраняются в `User` при создании договора
- [GET] `/owner/employees/{employee_id}`  — (apps/web/routes/owner.py)
- [GET] `/owner/employees/{employee_id}/edit`  — (apps/web/routes/owner.py) — форма редактирования профиля сотрудника (имя, фамилия, телефон, email, дата рождения)
  - `employee_id` в URL — это `telegram_id` сотрудника (исправлено 27.11.2025: устранена ошибка поиска сотрудника по внутреннему ID вместо telegram_id)
- [POST] `/owner/employees/{employee_id}/edit`  — (apps/web/routes/owner.py) — сохранение изменений профиля сотрудника
- [GET] `/owner/object/{object_id}`  — (apps/web/routes/owner_timeslots.py)
- [GET] `/owner/object/{object_id}/create`  — (apps/web/routes/owner_timeslots.py)
- [POST] `/owner/object/{object_id}/create`  — (apps/web/routes/owner_timeslots.py)
- [GET] `/owner/objects`  — (apps/web/routes/objects.py)
  - Query: `view_mode=cards|list` (default: list, редирект если не указан)
  - Query: `q_name` — фильтр по названию (клиентский фильтр, мгновенный поиск)
  - Query: `q_address` — фильтр по адресу (клиентский фильтр, мгновенный поиск)
  - Query: `sort_by` — сортировка (name, address)
  - Query: `sort_order` — направление сортировки (asc, desc)
  - **Фильтры:** Клиентские фильтры по названию и адресу в заголовках столбцов
  - **Сортировка:** При клике по столбцам, индикатор только на активном столбце
- [GET] `/owner/objects/create`  — (apps/web/routes/owner.py)
- [POST] `/owner/objects/create`  — (apps/web/routes/owner.py)
- [GET] `/owner/objects/{object_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/objects/{object_id}/delete`  — (apps/web/routes/owner.py)
- [GET] `/owner/objects/{object_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/objects/{object_id}/edit`  — (apps/web/routes/owner.py)
- [GET] `/owner/profile`  — (apps/web/routes/owner.py)
- [GET] `/owner/profile/preview`  — (apps/web/routes/owner.py)
- [POST] `/owner/profile/save`  — (apps/web/routes/owner.py)
- [POST] `/owner/profile/api/autosave`  — (apps/web/routes/owner.py) — автосохранение полей профиля (JSON API)
  - Поддерживает: `about_company`, `values`, `contact_phone`, `contact_messengers`, `photos`
  - Debounce: 600мс для текстовых полей, моментально для чекбоксов
  - См. [Owner Profile Autosave](/doc/vision_v1/roles/owner_profile_autosave.md)
- [GET] `/owner/profile/tags/{category}`  — (apps/web/routes/owner.py)
- [GET] `/owner/reports`  — (apps/web/routes/owner.py)
- [POST] `/owner/reports/generate`  — (apps/web/routes/owner.py)
- [GET] `/owner/reports/stats/period`  — (apps/web/routes/owner.py)
- [GET] `/owner/reviews`  — (apps/web/routes/owner_reviews.py)
- [GET] `/owner/settings`  — (apps/web/routes/owner.py)
- [GET] `/owner/shifts`  — (apps/web/routes/owner_shifts.py) — список смен с фильтрацией и пагинацией
  - Query: `status` — фильтр по статусу (active, planned, completed)
  - Query: `date_from`, `date_to` — период (YYYY-MM-DD)
  - Query: `object_id` — фильтр по объекту
  - Query: `q_user` — фильтр по сотруднику (Фамилия Имя, клиентский фильтр)
  - Query: `q_object` — фильтр по объекту (название, клиентский фильтр)
  - Query: `sort` — сортировка (id, user_name, object_name, planned_start, status)
  - Query: `order` — направление сортировки (asc, desc)
  - Query: `page`, `per_page` — пагинация (default: per_page=25)
  - **Фильтры:** Клиентский фильтр по сотруднику (мгновенный поиск), серверные фильтры по объекту, датам и статусу
  - **Сортировка:** По умолчанию по `planned_start` desc, сортировка по "Фамилия Имя" сотрудника
- [GET] `/owner/shifts/plan`  — (apps/web/routes/owner_shifts.py) — страница планирования смен
  - Query: `object_id` — ID объекта для предзаполнения
  - Query: `return_to` — URL для возврата после планирования (default: /owner/shifts)
  - **Замена:** Вместо модального окна на странице `/owner/shifts` теперь используется отдельная страница
- [GET] `/owner/shifts/api/schedule/{schedule_id}/object-id`  — (apps/web/routes/owner_shifts.py) — API для получения object_id из запланированной смены (JSON)
  - Используется в календаре для определения объекта при клике на запланированную смену
- [GET] `/owner/shifts/{shift_id}`  — (apps/web/routes/owner_shifts.py) — детали смены
  - Query: `shift_type` — тип смены (shift, schedule)
- [POST] `/owner/shifts/{shift_id}/cancel`  — (apps/web/routes/owner_shifts.py) — отмена смены
- [GET] `/owner/shifts_legacy`  — (apps/web/routes/owner.py)
- [GET] `/owner/shifts_legacy/{shift_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/shifts_legacy/{shift_id}/cancel`  — (apps/web/routes/owner.py)
- [GET] `/support`  — (apps/web/routes/support.py) — центр поддержки (хаб поддержки)
- [GET] `/support/bug`  — (apps/web/routes/support.py) — форма подачи бага
- [GET] `/support/faq`  — (apps/web/routes/support.py) — FAQ база знаний
- [GET] `/support/my-bugs`  — (apps/web/routes/support.py) — список моих багов
- [GET] `/owner/stats/summary`  — (apps/web/routes/owner_shifts.py)
- [GET] `/owner/tariff/change`  — (apps/web/routes/owner.py)
- [POST] `/owner/tariff/change`  — (apps/web/routes/owner.py)
- [GET] `/` — (apps/web/app.py) — лендинг (неавторизованным)
  - Источник тарифов: TariffService (active_only=True)
  - Разделы: геро-блок, «Почему выбирают…», «Тарифные планы» (после фич)
  - Карточки тарифов: цена/период, лимиты (−1 → «Безлимит»), локализованные фичи
  - Действие: «Выбрать тариф» → `/auth/register?tariff_id=...`
- [GET] `/owner/contract-templates` — (apps/web/routes/contract_templates.py) — управление шаблонами договоров (список, создание, редактирование)
- [GET] `/owner/templates`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/contracts`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/contracts/create`  — (apps/web/routes/owner.py)
- [POST] `/owner/templates/contracts/create`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/contracts/{template_id}`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/contracts/{template_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/templates/contracts/{template_id}/edit`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/planning`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/planning/create`  — (apps/web/routes/owner.py)
- [POST] `/owner/templates/planning/create`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/planning/{template_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/templates/planning/{template_id}/delete`  — (apps/web/routes/owner.py)
- [GET] `/owner/templates/planning/{template_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/templates/planning/{template_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/timeslots/bulk-edit`  — (apps/web/routes/owner.py)
- [GET] `/owner/timeslots/{timeslot_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/timeslots/{timeslot_id}/delete`  — (apps/web/routes/owner.py)
- ~~[GET] `/owner/timeslots/{timeslot_id}/edit`~~  — **УСТАРЕЛО** (закомментировано в apps/web/routes/owner.py, используй owner_timeslots.py)
- ~~[POST] `/owner/timeslots/{timeslot_id}/edit`~~  — **УСТАРЕЛО** (закомментировано в apps/web/routes/owner.py, используй owner_timeslots.py)
- [GET] `/owner/{shift_id}`  — (apps/web/routes/owner_shifts.py)
- [POST] `/owner/{shift_id}/cancel`  — (apps/web/routes/owner_shifts.py)
- [POST] `/owner/{timeslot_id}/delete`  — (apps/web/routes/owner_timeslots.py) — удаление тайм-слота
- [GET] `/owner/{timeslot_id}/edit`  — (apps/web/routes/owner_timeslots.py) — **ОСНОВНОЙ РОУТ** для редактирования тайм-слота
- [POST] `/owner/{timeslot_id}/edit`  — (apps/web/routes/owner_timeslots.py) — **ОСНОВНОЙ РОУТ** для обновления тайм-слота

## Онбординг владельца (регистрация/первый вход)
- Регистрация: `/auth/register` отправляет PIN в Telegram и редиректит на `/auth/login?success=...&telegram_id=...`.
- Форма логина автоподставляет `telegram_id` из query; PIN никогда не подставляется автоматически.
- Первый вход (идемпотентно): если нет активной подписки — назначается активный тариф с `is_popular=true` (самый дешёвый среди активных); список включённых фич берётся строго из `tariff_plans.features` и записывается в `OwnerProfile.enabled_features`.

## Дашборд владельца
- «Мои объекты»: полная таблица объектов владельца.
  - Колонки: Объект, Адрес, Статус (Открыт/Закрыт), Время (последнее изменение статуса: opened_at/closed_at из `ObjectOpening`).
  - При количестве записей >10 в таблице — вертикальный скролл блока.
- «Быстрые действия»: 5 тематических блоков, блоки с фичами в disabled-состоянии до их включения (CTA «Как включить?» → профиль).
- «Полезные ссылки»: выводятся в строку.

## Шаблоны (Jinja2)
- `admin/limits_overview.html`
- `owner/applications.html`
- `owner/calendar/analysis.html`
- `owner/calendar/index.html`
  - Стартовая загрузка только текущего месяца, скролл догружает следующий (`universal_calendar.js`)
  - Клики по тайм-слоту → общая модалка `plan_shift_modal.js`; по запланированной смене → `/owner/shifts/plan` с `employee_id` и `return_to` (фильтры `object_id`, `org_unit_id` сохраняются)
- `owner/calendar/week.html`
- `owner/change_tariff.html`
- `owner/dashboard.html`
- `owner/limits_dashboard.html`
- `owner/objects/create.html`
- `owner/objects/detail.html`
- `owner/objects/edit.html`
- `owner/objects/list.html`
- `owner/profile/index.html`
- `owner/reports/index.html`
- `owner/reviews.html`
- `owner/settings.html`
- `owner/shifts/access_denied.html`
- `owner/shifts/detail.html`
- `owner/shifts/list.html` — список смен с фильтрацией и пагинацией
  - Фильтры: клиентский фильтр по сотруднику (мгновенный поиск), серверные фильтры по объекту, датам и статусу
  - Сортировка по столбцам (ID, Сотрудник, Объект, Дата, Статус)
  - Пагинация: "Первая", "Назад", "X / Y", "Вперед", "Последняя" с выбором количества на странице (25, 50, 100)
  - Отображение сотрудника: "Фамилия Имя" с сортировкой по фамилии, затем имени
- `owner/shifts/plan.html` — страница планирования смен (замена модального окна)
  - Календарь: 5 недель (35 дней), адаптивная высота
  - Тайм-слоты показывают первый доступный свободный интервал (жирным), статус «Свободен» / «Частично свободен»
  - Отдельный список «Запланированные смены» (выделены и помечены бейджем «Запланировано») — можно снять галочку для отмены
  - Каждая карточка отображает свободные промежутки по всем трекам (`max_employees`)
  - Фильтрация сотрудников по выбранному объекту через API, `preselectedEmployeeId` передаётся из календаря
  - Информация в футере: объект + счётчик слотов (слева), кнопки (справа)
  - Параметр `return_to` для возврата на исходную страницу (календарь или список смен) с сохранёнными фильтрами
- `owner/shifts/not_found.html`
- `owner/templates/contracts/detail.html`
- `owner/templates/contracts/edit.html`
- `owner/timeslots/create.html` — форма создания тайм-слота (удалено поле "Игнорировать задачи объекта")
- `owner/timeslots/edit.html` — форма редактирования тайм-слота (удалено поле "Игнорировать задачи объекта")
- `owner/employees/create.html` — форма создания сотрудника с полями профиля и договора
- `owner/employees/edit.html` — форма редактирования профиля сотрудника (имя, фамилия, телефон, email, дата рождения)
- `support/hub.html` — центр поддержки (использует base_template для роли, блок content)
- `support/bug.html` — форма подачи бага (использует base_template для роли, блок content)
- `support/faq.html` — FAQ база знаний (использует base_template для роли, блок content)
- `support/my_bugs.html` — список моих багов (использует base_template для роли, блок content)
- `owner/timeslots/detail.html`
- `owner/timeslots/edit.html`
- `owner/timeslots/list.html`

## Общий календарь (Shared API)
- [GET] `/api/calendar/data`
- [GET] `/api/calendar/timeslots`
- [GET] `/api/calendar/shifts`
- [GET] `/api/calendar/stats`
- [GET] `/api/calendar/objects`

## Начисления и выплаты (Payroll) — Итерация 23
- [GET] `/owner/payroll` — (apps/web/routes/payroll.py) — начисления сотрудников с двумя вкладками
  - По умолчанию открывается «Сводка по сотрудникам»: агрегированные показатели (количество начислений, общая сумма, последний период) с сортировкой по ФИО/количеству/сумме/периоду, фильтрами по периоду и объекту, переключателем «Показать уволенных сотрудников».
  - Вкладка «Начисления» отображает плоский список записей (sort/pagination как на странице смен). Фильтр «Сотрудник» работает по пересечению периода договора (`start_date` vs `COALESCE(end_date, termination_date)`), поддерживает уволенных сотрудников.
- [GET] `/owner/payroll/report` — (apps/web/routes/payroll.py) — HTML-отчёт по начислениям и выплатам на выбранный период с вкладками «Отчёт по начислениям» / «Отчёт по выплатам», кнопками печати и экспорта.
- [GET] `/owner/payroll/report/export` — (apps/web/routes/payroll.py) — Excel-файл с двумя листами («Отчет по начислениям», «Отчет по выплатам»), структура соответствует экранному отчёту.
- [GET] `/owner/payroll/{entry_id}` — (apps/web/routes/payroll.py) — детализация начисления
  - В верхней части отображается сводная таблица всех начислений сотрудника (ID, период, сумма, статус), текущая запись подсвечена. Переходы из вкладки «Начисления» сохраняют выбранное начисление, из «Сводки по сотрудникам» — автоматически выделяется последнее начисление.
  - Раздел «Выплаты» располагается перед протоколом изменений. Кнопки создания удержаний/доплат и выплат автоматически блокируются, если зафиксированы выплаты.
- [POST] `/owner/payroll/{entry_id}/add-deduction` — (apps/web/routes/payroll.py) — добавить удержание (через PayrollAdjustmentService)
- [POST] `/owner/payroll/{entry_id}/add-bonus` — (apps/web/routes/payroll.py) — добавить доплату (через PayrollAdjustmentService)
- [POST] `/owner/payroll/{entry_id}/create-payment` — (apps/web/routes/payroll.py) — записать выплату (создаёт EmployeePayment со статусом pending)
- [POST] `/owner/payroll/{entry_id}/payments/{payment_id}/complete` — (apps/web/routes/payroll.py) — подтвердить выплату (pending → completed)
- [POST] `/owner/payroll/manual-recalculate` — (apps/web/routes/payroll.py) — ручной пересчёт выплат на выбранную дату (идемпотентно: обновляет существующие, создаёт недостающие)
  - Включает terminated контракты с `settlement_policy='termination_date'`, если конец платёжного периода ≤ `termination_date`.
- [GET] `/owner/payroll/statement/{employee_id}` — страница расчётного листа сотрудника (apps/web/routes/payroll.py)
  - Сервис `PayrollStatementService` гарантирует наличие всех начислений по корректировкам (досоздаёт по графику выплат, если нужно).
  - UI показывает итог по корректировкам/начислениям/выплатам + кнопки «Печать» и «Экспорт».
- [GET] `/owner/payroll/statement/{employee_id}/export` — Excel-версия расчётного листа (общий helper `build_statement_workbook`).

## Графики выплат (Payment Schedules) — Итерация 23
- [GET] `/owner/payment-schedules/{schedule_id}/data` — (apps/web/routes/payment_schedule.py) — данные графика (JSON)
- [GET] `/owner/payment-schedules/{schedule_id}/view` — просмотр графика (HTML)
- [POST] `/owner/payment-schedules/create-custom` — (apps/web/routes/payment_schedule.py) — создать кастомный график
- [PUT] `/owner/payment-schedules/{schedule_id}/edit` — (apps/web/routes/payment_schedule.py) — редактировать кастомный график
- [DELETE] `/owner/payment-schedules/{schedule_id}/delete` — (apps/web/routes/payment_schedule.py) — удалить кастомный график (мягкое удаление, проверка использования)
- [GET] `/owner/payment-schedules/available` — список доступных графиков

## Корректировки начислений (Payroll Adjustments) — Итерация 23
- [GET] `/owner/payroll-adjustments` — (apps/web/routes/owner_payroll_adjustments.py) — список всех корректировок с фильтрами
  - Отбор: корректировки, относящиеся к объектам владельца напрямую (`object_id`) или к расписаниям смен на объектах владельца (через `shift_schedule.object_id`). Фильтрация по договорным сотрудникам не обязательна.
  - Query: `adjustment_type` — тип корректировки (shift_base, late_start, task_bonus, task_penalty, manual_bonus, manual_deduction)
  - Query: `employee_id` — ID сотрудника (строка, конвертируется в int)
  - Query: `object_id` — ID объекта (строка, конвертируется в int)
  - Query: `is_applied` — статус применения (all/applied/unapplied)
  - Query: `date_from`, `date_to` — период (YYYY-MM-DD)
  - Query: `page`, `per_page` — пагинация
  - Выпадающие списки сотрудников (фильтр, модалка «Добавить начисление») получают данные из `EmployeeSelectorService`: активные сотрудники идут первыми, затем разделитель «Бывшие» (жирный курсив) и архивные сотрудники (курсив).
- [POST] `/owner/payroll-adjustments/create` — (apps/web/routes/owner_payroll_adjustments.py) — создать ручную корректировку
  - Form: `employee_id`, `adjustment_type`, `amount`, `description`, `adjustment_date` (дата начисления), `object_id` (опц), `shift_id` (опц)
  - **Важно:** `adjustment_date` устанавливает `created_at` корректировки на указанную дату
- [POST] `/owner/payroll-adjustments/{adjustment_id}/edit` — (apps/web/routes/owner_payroll_adjustments.py) — редактировать корректировку (только ручные неприменённые)
- [GET] `/owner/payroll-adjustments/{adjustment_id}/history` — (apps/web/routes/owner_payroll_adjustments.py) — история изменений (JSON)

## Организационная структура (Org Structure) — Итерация 23
- [GET] `/owner/org-structure` — (apps/web/routes/org_structure.py) — страница "Организация и финансы"
  - **Комплексная страница:** иерархия подразделений + графики выплат + системы оплаты
  - **Split-view дизайн:** левая панель (графики и системы), правая панель (детали графика)
  - **Наследование настроек:** effective_payment_schedule_id / effective_payment_system_id рассчитываются в OrgStructureService.get_org_tree
  - **UI:** отображает унаследованные значения для подразделений без прямых привязок
  - **Шаблон:** `owner/org_structure/list.html` (включает `modals.html`)
  - **Удалено:** `/owner/payment-systems` (функционал интегрирован сюда)
- [POST] `/owner/org-structure/create` — (apps/web/routes/org_structure.py) — создать подразделение
- [POST] `/owner/org-structure/{unit_id}/edit` — (apps/web/routes/org_structure.py) — редактировать подразделение
- [POST] `/owner/org-structure/{unit_id}/delete` — (apps/web/routes/org_structure.py) — удалить подразделение (soft delete)
- [POST] `/owner/org-structure/{unit_id}/move` — (apps/web/routes/org_structure.py) — переместить подразделение
- [GET] `/owner/org-structure/{unit_id}/data` — (apps/web/routes/org_structure.py) — получить данные (JSON)
- [GET] `/owner/org-structure/schedules-usage` — (apps/web/routes/org_structure.py) — статистика использования графиков выплат (с учетом наследования)
  - **Возвращает:** `[{schedule_id, units_count}]` — считает по effective_payment_schedule_id
- [GET] `/owner/org-structure/systems-usage` — (apps/web/routes/org_structure.py) — статистика использования систем оплаты (с учетом наследования)
  - **Возвращает:** `[{system_id, count}]` — считает по effective_payment_system_id
- [GET] `/owner/org-structure/schedule-stats/{schedule_id}` — (apps/web/routes/org_structure.py) — детальная статистика графика
  - **Возвращает:** `{units: [{id, name, objects_count}], objects: int, employees: int}`
  - **Логика:** фильтрация по effective_payment_schedule_id, подсчет сотрудников через Shift
- **JS:** `PaymentScheduleEditor` используется для генерации превью графика с учетом смещения (периоды, дни)

## Задачи на смену (Shift Tasks) — Итерация 23
- [GET] `/owner/shift-tasks` — (apps/web/routes/owner.py) — список всех задач по сменам
  - Query: `object_id` — фильтр по объекту
  - Query: `is_completed` — фильтр по выполнению
  - Query: `is_mandatory` — фильтр по обязательности
- Задачи настраиваются в формах объектов и тайм-слотов

## UI/UX — Итерация 25
### Базовый шаблон
- `apps/web/templates/owner/base_owner.html` — новый дизайн с топбаром и сайдбаром

### Статические файлы
- `apps/web/static/css/owner/sidebar.css` — стили сайдбара (коллапсируемый, адаптивный)
- `apps/web/static/js/owner/sidebar.js` — интерактивность сайдбара (toggle, аккордеон, localStorage, shortcuts)

### Структура навигации
- **Топбар:** логотип, toggle сайдбара, уведомления, переключатель ролей, профиль
- **Сайдбар:** (240px развернут, 64px свернут)
  - 🏠 Главная
  - 📅 Планирование (Календарь, Смены, Тайм-слоты)
  - 👥 Персонал (Сотрудники, Заявки, Подразделения)
  - 🏢 Объекты
  - 💰 Финансы (Выплаты, Начисления, Системы оплаты, Отчеты)
  - ⭐ Отзывы
  - ⚙️ Настройки (Профиль, Тарифы, Лимиты)

### Клавиатурные shortcuts
- `Cmd/Ctrl + B` — toggle сайдбара
- `Cmd/Ctrl + 1-7` — быстрые переходы по разделам
- `Escape` — закрыть сайдбар (мобильные)

### Адаптивность
- **Десктоп (>1024px):** свернут до иконок, разворачивается при hover/клике
- **Планшет (768-1024px):** скрыт, открывается через overlay
- **Мобильный (<768px):** fullscreen drawer снизу
