# Роль: Сотрудник (Employee)

## Роуты и эндпоинты
- [GET] `/employee/`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/applications`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/applications/{application_id}`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/applications/{application_id}/interview`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/calendar/data`  — (apps/web/routes/employee.py) — универсальные данные календаря (тайм-слоты + смены) с расчётом свободных интервалов
- [GET] `/employee/calendar/api/timeslot/{timeslot_id}` — (apps/web/routes/employee.py) — детали тайм-слота для модалки быстрого планирования (занятость по трекам, свободные интервалы)
- [GET] `/employee/api/calendar/employees-for-object/{object_id}`  — (apps/web/routes/employee.py) — возвращает текущего сотрудника, если у него есть доступ к объекту (используется общим планировщиком)
- [POST] `/employee/api/calendar/check-availability` — (apps/web/routes/employee.py) — проверка доступности сотрудника при выборе тайм-слота/интервала
- [POST] `/employee/api/calendar/plan-shift`  — (apps/web/routes/employee.py) — планирование смены для себя через общий планировщик (поддержка частичных интервалов)
  - Использует `Contract.get_effective_hourly_rate()` для определения ставки
  - Если `contract.use_contract_rate = True`: приоритет ставки договора
  - Если `contract.use_contract_rate = False`: тайм-слот > объект
- [GET] `/employee/api/employees`  — (apps/web/routes/employee.py)
- [GET] `/employee/api/objects`  — (apps/web/routes/employee.py)
- [POST] `/employee/api/shifts/cancel`  — (apps/web/routes/employee.py)
- [GET] `/employee/applications`  — (apps/web/routes/employee.py)
- [GET] `/employee/calendar`  — (apps/web/routes/employee.py)
- [GET] `/employee/calendar/api/objects`  — (apps/web/routes/employee.py)
- [GET] `/employee/earnings`  — (apps/web/routes/employee.py) — страница «Мой заработок»; годовая выборка, карточки сводных показателей, блок «Даты выплат» с фильтрацией начислений и таблица «Начисления» (столбец «Выплата» показывает дату фактической/запланированной выплаты)
  - Исправлено 27.11.2025: устранена проблема с lazy loading при получении графика выплат через цепочку наследования подразделений (используется SQL-запрос вместо рекурсивного вызова метода модели)
- [GET] `/employee/earnings/export`  — (apps/web/routes/employee.py) — экспорт годовой выборки заработка в XLSX (сводка + детальная таблица с колонкой «Выплата»)
- [GET] `/employee/history`  — (apps/web/routes/employee.py)
- [GET] `/employee/objects`  — (apps/web/routes/employee.py)
- [GET] `/employee/profile`  — (apps/web/routes/employee.py)
- [POST] `/employee/profile`  — (apps/web/routes/employee.py)
- [GET] `/employee/reviews`  — (apps/web/routes/employee_reviews.py)
- [GET] `/employee/shifts`  — (apps/web/routes/employee.py)
- [GET] `/employee/shifts/{shift_id}`  — (apps/web/routes/employee.py)
- [GET] `/employee/shifts/plan` — (apps/web/routes/employee.py) — страница планирования смен (аналог owner/manager) с предзаполнением текущего сотрудника и объекта
- [GET] `/support`  — (apps/web/routes/support.py) — центр поддержки (хаб поддержки)
- [GET] `/support/bug`  — (apps/web/routes/support.py) — форма подачи бага
- [GET] `/support/faq`  — (apps/web/routes/support.py) — FAQ база знаний
- [GET] `/support/my-bugs`  — (apps/web/routes/support.py) — список моих багов
- [GET] `/employee/timeslots/{timeslot_id}`  — (apps/web/routes/employee.py)

## Шаблоны (Jinja2)
- `employee/applications.html`
- `support/hub.html` — центр поддержки (использует base_template для роли, блок content)
- `support/bug.html` — форма подачи бага (использует base_template для роли, блок content)
- `support/faq.html` — FAQ база знаний (использует base_template для роли, блок content)
- `support/my_bugs.html` — список моих багов (использует base_template для роли, блок content)
- `employee/calendar.html`
  - Загрузка текущего месяца, дальнейшие месяцы подгружаются при скролле
  - Фильтр по объектам доступен сотруднику (как у владельца и управляющего), состояние фильтра сохраняется в URL (`object_id`)
  - Тайм-слоты → модалка `plan_shift_modal.js` (селект сотрудника заблокирован, всегда текущий пользователь)
  - Запланированные смены → `/employee/shifts/plan` c `return_to`, фильтры (`object_id`) восстанавливаются
  - После планирования смены через форму быстрого планирования календарь автоматически обновляется с сохранением фильтра по объектам
  - Курсор на пустых днях — `default`, кликабельны только тайм-слоты и смены
- `employee/earnings.html`
  - Переключатель года (фиксированный список доступных лет)
  - Карточка «Разбивка по объектам» (прокручиваемая, до 5 объектов)
  - Карточка «Даты выплат» (таблица с липким заголовком, автоматический скролл на текущий месяц, кнопка «Посмотреть» фильтрует таблицу «Начисления»)
    - Исправлено 27.11.2025: устранена проблема с отображением раздела «Даты выплат» из-за lazy loading при рекурсивном получении графика выплат через цепочку наследования подразделений
  - Таблица «Начисления» с колонкой «Выплата» (дата выплаты или «—»), фильтрация синхронизирована с блоком «Даты выплат», итоговая строка показывает общие часы и сумму за год
- `employee/history.html`
- `employee/index.html`
- `employee/objects.html`
- `employee/profile.html`
- `employee/reviews.html`
- `employee/shifts/detail.html`
- `employee/shifts/list.html`
- `employee/shifts/plan.html` — страница планирования смен сотрудника (общий `plan_shift.js`, режим `role: 'employee'`)
  - Выбранный объект подставляется из запроса или кликнутого тайм-слота
  - Секция «Запланированные смены» выводится аналогично owner/manager, разрешены отмена и планирование в одной форме
  - Макет выровнен с менеджером: сетка календаря, заголовки недель, блок сотрудников
- `employee/timeslots/detail.html`

### Особенности календаря/планировщика
- Общая модалка `plan_shift_modal.js`: tabs «Время смены N», слайдеры автоматически занимают свободный интервал, если свободного времени нет — выводится соответствующее сообщение.
- Общий `plan_shift.js` в режиме `role: 'employee'`: селект сотрудника скрыт, используются только тайм-слоты, доступные текущему пользователю; отмена и планирование доступны одновременно.

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
