# Правила деления кода по разделам (Cursor division rules)

Цель: поддерживать маленькие и изолированные файлы, соответствующие конкретному разделу рабочего пространства (owner, employee, superadmin и т.д.), чтобы не допускать «мегамодулей» вроде `owner.py`.

## Базовые принципы

- Разделяй код по доменам и подсекциям интерфейса (DDD + @move.md).
- Один файл — одна ответственность (Single Responsibility).
- Логика не смешивается между разделами (owner ≠ employee ≠ superadmin).
- Никаких «временных свалок» — если код временно скопирован, он всё равно должен стать отдельным модулем.

## Структура для веб-роутов

Рекомендуемая структура в `apps/web/routes/`:

- `owner/`
  - `owner_calendar.py` — календарь владельца (`/owner/calendar/*`)
  - `owner_timeslots.py` — тайм-слоты (`/owner/timeslots/*`)
  - `owner_shifts.py` — смены (`/owner/shifts/*`)
  - `owner_employees.py` — сотрудники (`/owner/employees/*`)
  - `owner_contracts.py` — договоры сотрудников (`/owner/employees/contract/*`)
  - `owner_templates_contracts.py` — шаблоны договоров (`/owner/templates/contracts/*`)
  - `owner_templates_planning.py` — шаблоны планирования (`/owner/templates/planning/*`)

- `employee/` (по аналогии)
- `superadmin/` (по аналогии)

Файл-агрегатор допускается только для подключения роутеров:

```python
# apps/web/routes/owner/__init__.py
from fastapi import APIRouter

from .owner_calendar import router as calendar_router
from .owner_timeslots import router as timeslots_router
from .owner_shifts import router as shifts_router
from .owner_employees import router as employees_router
from .owner_contracts import router as contracts_router
from .owner_templates_contracts import router as tpl_contracts_router
from .owner_templates_planning import router as tpl_planning_router

router = APIRouter()
router.include_router(calendar_router, prefix="/owner", tags=["owner:calendar"])
router.include_router(timeslots_router, prefix="/owner", tags=["owner:timeslots"])
router.include_router(shifts_router, prefix="/owner", tags=["owner:shifts"])
router.include_router(employees_router, prefix="/owner", tags=["owner:employees"])
router.include_router(contracts_router, prefix="/owner", tags=["owner:contracts"])
router.include_router(tpl_contracts_router, prefix="/owner", tags=["owner:templates:contracts"])
router.include_router(tpl_planning_router, prefix="/owner", tags=["owner:templates:planning"])
```

В `apps/web/app.py` подключается только агрегатор `apps/web/routes/owner`.

## Шаблоны (templates)

- Хранить строго зеркально путям роутов: `apps/web/templates/owner/...`
- Базовый шаблон для владельца — `owner/base_owner.html`.
- Внутренние ссылки всегда указывать с префиксом раздела (`/owner/...`).

## Сервисы

- Сервисы класть в `apps/web/services/` и делить по предметным областям, а не по страницам.
- Избегать импортов «поверх разделов», если это ведёт к циклам; использовать абстракции.

## Ограничения размера и содержания файла

- Жёсткий ориентир: до ~300–400 строк на файл маршрутов. Если больше — разделить.
- В файлах роутов — только маршруты и минимальная композиция сервисов/валидаций.
- Никакой бизнес-логики в роутерах — только вызовы сервисов и сбор контекста для шаблонов.

## Правила переноса кода (@move.md)

- При переносе рабочего кода разрешено менять только пути, импорты и ссылки в шаблонах.
- Структуру данных, имена полей и алгоритмы — не менять.
- Форматирование — в шаблонах, а не в Python-коде.

## Именование

- Префиксировать файлы разделом: `owner_*`, `employee_*`, `superadmin_*`.
- Имена роут-тегов: `owner:calendar`, `owner:timeslots`, и т.д.

## Подключение зависимостей

- Использовать `apps/web/dependencies` (например, `get_current_user_dependency`, `require_role`).
- Сессии БД — через зависимости (`get_db_session`/`get_async_session`).

## Рефакторинг существующего «мегамодуля»

Если существует большой файл (например, `owner.py`):
1. Создай подпакет `apps/web/routes/owner/`.
2. Вырежи логически цельные блоки (календарь, смены, тайм-слоты и т.д.) в отдельные файлы.
3. Добавь агрегатор в `apps/web/routes/owner/__init__.py` (см. пример выше).
4. Обнови подключения в `apps/web/app.py`.
5. Проверь соответствие @move.md.

## Проверки перед PR

- Файлы не превышают рекомендованный размер.
- Разделение по подпакетам соответствует разделам интерфейса.
- Все пути и базовые шаблоны корректны для нового пространства (`/owner/*`).
- Нет «мёртвых» импортов и циклических зависимостей.

---

Этот файл обязателен к соблюдению при добавлении новых разделов и переносе существующих.


