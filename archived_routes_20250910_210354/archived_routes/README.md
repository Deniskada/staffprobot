# Архив перенесенного кода в /owner/*

Этот архив содержит код, который был перенесен из корневых маршрутов в пространство `/owner/*`.

## Перенесенные файлы:

### Роуты:
- `calendar.py` → `owner.py` (календарь)
- `reports.py` → `owner.py` (отчеты)
- `profile.py` → `owner.py` (профиль владельца)
- `timeslots.py` → `owner.py` (тайм-слоты)
- `shifts.py` → `owner.py` (смены)
- `objects.py` → `owner.py` (объекты)
- `employees.py` → `owner.py` (сотрудники)
- `contracts.py` → `owner.py` (договоры)
- `templates.py` → `owner.py` (шаблоны)

### Шаблоны:
- `templates/calendar/` → `templates/owner/calendar/`
- `templates/reports/` → `templates/owner/reports/`
- `templates/profile/` → `templates/owner/profile/`
- `templates/timeslots/` → `templates/owner/timeslots/`
- `templates/shifts/` → `templates/owner/shifts/`
- `templates/objects/` → `templates/owner/objects/`
- `templates/employees/` → `templates/owner/employees/`
- `templates/contracts/` → `templates/owner/contracts/`
- `templates/templates/` → `templates/owner/templates/`

## Дата архивирования:
$(date)

## Примечание:
Весь функционал был перенесен в `apps/web/routes/owner.py` и соответствующие шаблоны в `apps/web/templates/owner/`.
