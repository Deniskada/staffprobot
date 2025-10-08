# Общий компонент: Календарь

## Shared API

### Основные эндпоинты календаря
- [GET] `/owner/calendar/api/data` — (apps/web/routes/owner.py) данные календаря владельца с кэшированием (TTL 2 мин)
- [GET] `/manager/calendar/api/data` — (apps/web/routes/manager.py) данные календаря управляющего с кэшированием (TTL 2 мин)
- [GET] `/employee/api/calendar/data` — (apps/web/routes/employee.py) данные календаря сотрудника с кэшированием (TTL 2 мин)

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

- **Производительность:**
  - Ускорение календаря: 98.1-98.8% (459 мс → 5 мс)
  - Ускорение панелей: ~98% (240-260 мс → <5 мс)
  - Hit Rate: 71-74%

## Shared сервисы
- `shared/services/calendar_filter_service.py` — CalendarFilterService с кэшированием методов _get_timeslots() и _get_shifts()

## Shared шаблоны
- `templates/shared/calendar/*` (grid, timeslot, navigation, shift)

## Shared JS/CSS
- `static/js/shared/universal_calendar.js` — универсальный менеджер календаря
- `static/js/shared/calendar.js` — вспомогательные функции
- `static/js/shared/calendar_panels.js` — панели drag&drop с кэшем в памяти (objectsData, employeesData)
