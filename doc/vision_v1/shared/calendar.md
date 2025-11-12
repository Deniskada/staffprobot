# Общий компонент: Календарь

## Shared API

### Основные эндпоинты календаря
- [GET] `/owner/calendar/api/data` — (apps/web/routes/owner.py) данные календаря владельца с кэшированием (TTL 2 мин)
- [GET] `/manager/calendar/api/data` — (apps/web/routes/manager.py) данные календаря управляющего с кэшированием (TTL 2 мин)
- [GET] `/employee/api/calendar/data` — (apps/web/routes/employee.py) данные календаря сотрудника с кэшированием (TTL 2 мин)
- [GET] `/owner/calendar/api/timeslot/{timeslot_id}` / `/manager/calendar/api/timeslot/{timeslot_id}` / `/employee/calendar/api/timeslot/{timeslot_id}` — детальные данные тайм-слота для модалки быстрого планирования (распределение по трекам, занятые интервалы, локализованные времена)
- [POST] `/owner/api/calendar/check-availability`, `/manager/api/calendar/check-availability`, `/employee/api/calendar/check-availability` — проверка доступности сотрудника перед планированием частичного интервала
- [POST] `/owner/api/calendar/plan-shift`, `/manager/api/calendar/plan-shift`, `/employee/api/calendar/plan-shift` — планирование смены для выбранного сотрудника (поддержка частичных интервалов и очистка кэша `calendar_shifts:*`, `api_response:*`)
- [GET] `/owner/api/calendar/employees-for-object/{object_id}`, `/manager/api/employees/for-object/{object_id}`, `/employee/api/calendar/employees-for-object/{object_id}` — выдача списка сотрудников для общего планировщика (у сотрудника возвращается только текущий пользователь, если объект доступен)

### Панели объектов
- [GET] `/owner/calendar/api/objects` — (apps/web/routes/owner.py) список объектов для drag&drop с кэшированием (TTL 2 мин)
- [GET] `/manager/calendar/api/objects` — (apps/web/routes/manager.py) список объектов для drag&drop с кэшированием (TTL 2 мин)
- [GET] `/employee/calendar/api/objects` — (apps/web/routes/employee.py) объекты с активными контрактами с кэшированием (TTL 2 мин)
- [GET] `/employee/api/objects` — (apps/web/routes/employee.py) публичные объекты для карты с кэшированием (TTL 5 мин)

### Панели сотрудников
- [GET] `/owner/api/employees` — (apps/web/routes/owner.py) список сотрудников для drag&drop с кэшированием (TTL 2 мин)
- [GET] `/manager/api/employees` — (apps/web/routes/manager.py) список сотрудников для drag&drop с кэшированием (TTL 2 мин)

### Кэширование
- **Типы кэша:**
  - `calendar_timeslots:*` — тайм-слоты (TTL 10 мин, декоратор @cached)
  - `calendar_shifts:*` — смены (TTL 3 мин, декоратор @cached)
  - `api_response:*` — JSON-ответы календаря (TTL 2 мин)
  - `api_objects:*` — JSON-ответы панелей объектов (TTL 2 мин)
  - `api_employees:*` — JSON-ответы панелей сотрудников (TTL 2 мин)

- **Инвалидация:**
  - При create/update/delete тайм-слота → `calendar_timeslots:*`, `calendar_shifts:*`, `api_response:*`, `api_objects:*`
  - При открытии/закрытии смены → `calendar_shifts:*`, `api_response:*`
  - При изменении контракта → `api_employees:*`, `api_objects:*`
  - При изменении объекта → `api_objects:*`, включая `api_objects:employee_*`

- **Мониторинг:**
  - `/admin/cache/stats` — сгруппировать отдельный блок «Calendar» (TODO) для префиксов `calendar_*`.
  - `/admin/monitoring` — графики Prometheus: `staffprobot_http_request_duration_seconds{endpoint="/<role>/calendar/api/data"}`, `staffprobot_cache_hit_ratio`, `staffprobot_db_query_duration_seconds{table="time_slots"}`.

- **Производительность:**
  - Ускорение календаря: 98.1-98.8% (459 мс → 5 мс)
  - Ускорение панелей: ~98% (240-260 мс → <5 мс)
  - Hit Rate: 71-74%

## Shared сервисы
- `shared/services/calendar_filter_service.py` — CalendarFilterService с кэшированием методов _get_timeslots() и _get_shifts()

## Shared шаблоны
- `templates/shared/calendar/*` (grid, timeslot, navigation, shift)
- Модалка быстрого планирования формируется полностью в `plan_shift_modal.js` и подключается на страницах календаря всех ролей

## Shared JS/CSS
- `static/js/shared/universal_calendar.js` — универсальный менеджер календаря с ленивой подгрузкой месяцев (scroll → `loadMonthRange()`), повторным `renderCalendarGrid` и сохранением позиции скролла
- `static/js/shared/calendar.js` — вспомогательные функции
- `static/js/shared/calendar_panels.js` — панели drag&drop с кэшем в памяти (objectsData, employeesData)
- `static/js/shared/plan_shift_modal.js` — общий модуль модального быстрого планирования (tabs «Время смены N», рендер шкалы по трекам, автоматический выбор свободного интервала, снэппинг 30 мин, блокировка селекта у роли employee)
- `static/js/shared/plan_shift.js` — общий полноэкранный планировщик (страницы `/owner/manager/employee/shifts/plan`), конфигурируется через `window.planShiftConfig`:
  - `role` ∈ {owner, manager, employee}
  - `hideEmployeeSelect=true` — для сотрудника (селект скрыт и заблокирован)
  - `preselectedEmployeeId` — предзаполненный сотрудник при переходе с календаря (клик по смене/тайм-слоту)
  - Автоматический пересчёт свободных интервалов по всем трекам (`max_employees`), отображение первой свободной «щели» (+ bold в UI) и уже запланированных смен с бейджем «Запланировано»
  - Единая логика отмены/планирования (очистка `calendar_shifts:*`, `api_response:*` после успешного действия)

## Динамическая загрузка

- Стартовая загрузка охватывает только текущий месяц (рассчитывается в `calculateDateRange()`).
- Прокрутка инициирует `handleScroll()` → `checkAndLoadAdjacentMonths()` → `loadMonthRange()`. Диапазон по умолчанию: текущий месяц + следующий.
- После получения данных вызывается `mergeMonthData()` + `processCalendarData()`, затем `onDataLoaded` перерисовывает сетку (`renderCalendarGrid`) и обновляет `window.calendarData`.

## Модальное окно планирования

- Tabs «Время смены N» создаются по `max_employees`. Каждый таб содержит собственный `scheduler-wrapper` с:
  - сплошное выделение свободного диапазона зелёным;
  - занятые интервалы (красные сегменты) только для текущего трека;
  - слайдеры, которые «прилипают» к границам свободного сегмента и к ближайшим сменам (шаг 30 минут).
- Автозаполнение:
  - При открытии модалки и при переключении таба имитируется клик по кнопке свободного времени — слайдеры расширяются на весь доступный интервал.
  - Если свободного времени нет, блок кнопок и слайдеры скрываются, вместо надписи “Начало/Окончание” показывается сообщение «Все доступное время занято».
- Кнопка «Добавить» активна только при выбранном сотруднике и валидном интервале. Для роли employee селект сотрудника недоступен, идентификатор берётся из текущего пользователя.

## Страницы `/role/shifts/plan`

- Отображают:
  - Свободные тайм-слоты с учётом новой логики свободного времени (первый свободный интервал выделен жирным).
  - Запланированные смены сотрудника (бейдж «Запланировано») с возможностью снять выделение для отмены.
- Поддерживают одновременное планирование новых смен и отмену выбранных, включая `return_to` для возврата в календарь с сохранёнными фильтрами (`object_id`, `org_unit_id`).
