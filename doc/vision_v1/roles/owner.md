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
- [POST] `/owner/api/calendar/plan-shift`  — (apps/web/routes/owner.py)
- [GET] `/owner/api/check/employee`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/check/feature/{feature}`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/check/manager`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/check/object`  — (apps/web/routes/limits.py)
- [GET] `/owner/api/contracts/my-contracts`  — (apps/web/routes/owner.py)
- [GET] `/owner/api/employees`  — (apps/web/routes/owner.py)
- [GET] `/owner/api/employees/for-object/{object_id}`  — (apps/web/routes/owner.py)
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
- [GET] `/owner/dashboard`  — (apps/web/routes/owner.py)
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
- [GET] `/owner/employees/{employee_id}`  — (apps/web/routes/owner.py)
- [GET] `/owner/object/{object_id}`  — (apps/web/routes/owner_timeslots.py)
- [GET] `/owner/object/{object_id}/create`  — (apps/web/routes/owner_timeslots.py)
- [POST] `/owner/object/{object_id}/create`  — (apps/web/routes/owner_timeslots.py)
- [GET] `/owner/objects`  — (apps/web/routes/owner.py)
- [GET] `/owner/objects/create`  — (apps/web/routes/owner.py)
- [POST] `/owner/objects/create`  — (apps/web/routes/owner.py)
- [GET] `/owner/objects/{object_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/objects/{object_id}/delete`  — (apps/web/routes/owner.py)
- [GET] `/owner/objects/{object_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/objects/{object_id}/edit`  — (apps/web/routes/owner.py)
- [GET] `/owner/profile`  — (apps/web/routes/owner.py)
- [GET] `/owner/profile/preview`  — (apps/web/routes/owner.py)
- [POST] `/owner/profile/save`  — (apps/web/routes/owner.py)
- [GET] `/owner/profile/tags/{category}`  — (apps/web/routes/owner.py)
- [GET] `/owner/reports`  — (apps/web/routes/owner.py)
- [POST] `/owner/reports/generate`  — (apps/web/routes/owner.py)
- [GET] `/owner/reports/stats/period`  — (apps/web/routes/owner.py)
- [GET] `/owner/reviews`  — (apps/web/routes/owner_reviews.py)
- [GET] `/owner/settings`  — (apps/web/routes/owner.py)
- [GET] `/owner/shifts_legacy`  — (apps/web/routes/owner.py)
- [GET] `/owner/shifts_legacy/{shift_id}`  — (apps/web/routes/owner.py)
- [POST] `/owner/shifts_legacy/{shift_id}/cancel`  — (apps/web/routes/owner.py)
- [GET] `/owner/stats/summary`  — (apps/web/routes/owner_shifts.py)
- [GET] `/owner/tariff/change`  — (apps/web/routes/owner.py)
- [POST] `/owner/tariff/change`  — (apps/web/routes/owner.py)
- [GET] `/` — (apps/web/app.py) — лендинг (неавторизованным)
  - Источник тарифов: TariffService (active_only=True)
  - Разделы: геро-блок, «Почему выбирают…», «Тарифные планы» (после фич)
  - Карточки тарифов: цена/период, лимиты (−1 → «Безлимит»), локализованные фичи
  - Действие: «Выбрать тариф» → `/auth/register?tariff_id=...`
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
- [GET] `/owner/timeslots/{timeslot_id}/edit`  — (apps/web/routes/owner.py)
- [POST] `/owner/timeslots/{timeslot_id}/edit`  — (apps/web/routes/owner.py)
- [GET] `/owner/{shift_id}`  — (apps/web/routes/owner_shifts.py)
- [POST] `/owner/{shift_id}/cancel`  — (apps/web/routes/owner_shifts.py)
- [POST] `/owner/{timeslot_id}/delete`  — (apps/web/routes/owner_timeslots.py)
- [GET] `/owner/{timeslot_id}/edit`  — (apps/web/routes/owner_timeslots.py)
- [POST] `/owner/{timeslot_id}/edit`  — (apps/web/routes/owner_timeslots.py)

## Шаблоны (Jinja2)
- `admin/limits_overview.html`
- `owner/applications.html`
- `owner/calendar/analysis.html`
- `owner/calendar/index.html`
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
- `owner/shifts/list.html`
- `owner/shifts/not_found.html`
- `owner/templates/contracts/detail.html`
- `owner/templates/contracts/edit.html`
- `owner/timeslots/create.html`
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
- [GET] `/owner/payroll` — (apps/web/routes/payroll.py) — список начислений всех сотрудников
- [GET] `/owner/payroll/{entry_id}` — (apps/web/routes/payroll.py) — детализация начисления с adjustments и payments
- [POST] `/owner/payroll/{entry_id}/add-deduction` — (apps/web/routes/payroll.py) — добавить удержание (через PayrollAdjustmentService)
- [POST] `/owner/payroll/{entry_id}/add-bonus` — (apps/web/routes/payroll.py) — добавить доплату (через PayrollAdjustmentService)
- [POST] `/owner/payroll/{entry_id}/create-payment` — (apps/web/routes/payroll.py) — записать выплату (создаёт EmployeePayment со статусом pending)
- [POST] `/owner/payroll/{entry_id}/payments/{payment_id}/complete` — (apps/web/routes/payroll.py) — подтвердить выплату (pending → completed)

## Графики выплат (Payment Schedules) — Итерация 23
- [GET] `/owner/payment-schedules/{schedule_id}/data` — (apps/web/routes/payment_schedule.py) — данные графика (JSON)
- [GET] `/owner/payment-schedules/{schedule_id}/view` — просмотр графика (HTML)
- [POST] `/owner/payment-schedules/create` — создать кастомный график
- [GET] `/owner/payment-schedules/available` — список доступных графиков

## Корректировки начислений (Payroll Adjustments) — Итерация 23
- [GET] `/owner/payroll-adjustments` — (apps/web/routes/owner_payroll_adjustments.py) — список всех корректировок с фильтрами
  - Query: `adjustment_type` — тип корректировки (shift_base, late_start, task_bonus, task_penalty, manual_bonus, manual_deduction)
  - Query: `employee_id` — ID сотрудника (строка, конвертируется в int)
  - Query: `object_id` — ID объекта (строка, конвертируется в int)
  - Query: `is_applied` — статус применения (all/applied/unapplied)
  - Query: `date_from`, `date_to` — период (YYYY-MM-DD)
  - Query: `page`, `per_page` — пагинация
- [POST] `/owner/payroll-adjustments/create` — (apps/web/routes/owner_payroll_adjustments.py) — создать ручную корректировку
- [POST] `/owner/payroll-adjustments/{adjustment_id}/edit` — (apps/web/routes/owner_payroll_adjustments.py) — редактировать корректировку
- [GET] `/owner/payroll-adjustments/{adjustment_id}/history` — (apps/web/routes/owner_payroll_adjustments.py) — история изменений (JSON)

## Организационная структура (Org Structure) — Итерация 23
- [GET] `/owner/org-structure` — (apps/web/routes/org_structure.py) — список подразделений (дерево)
- [POST] `/owner/org-structure/create` — создать подразделение
- [POST] `/owner/org-structure/{unit_id}/edit` — редактировать подразделение
- [POST] `/owner/org-structure/{unit_id}/delete` — удалить подразделение (soft delete)
- [POST] `/owner/org-structure/{unit_id}/move` — переместить подразделение
- [GET] `/owner/org-structure/{unit_id}/data` — получить данные (JSON)

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
