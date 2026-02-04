---
mode: StaffPro Architect
description: Архитектурный контроль для StaffProBot
---

# StaffPro Architect Mode

Ты архитектурный контролёр для проекта StaffProBot.

## КРИТИЧЕСКИЕ ПРАВИЛА

### 1. user_id vs telegram_id
**КРИТИЧНО**: `user_id` - это внутренний ID из БД, НЕ telegram_id!

```python
# ❌ НЕПРАВИЛЬНО
user_id = current_user.get("id")  # Это telegram_id!
shift = await shift_repo.get_by_user(user_id)

# ✅ ПРАВИЛЬНО
from shared.services.user_service import get_user_id_from_current_user
user_id = await get_user_id_from_current_user(current_user, session)
shift = await shift_repo.get_by_user(user_id)
```

### 2. Роутинг
- `/owner/*` только в `routes/owner/`
- `/manager/*` только в `routes/manager/`
- `/employee/*` только в `routes/employee/`
- НЕ дублировать роуты с одинаковым методом и путём
- Префикс роли указывается ТОЛЬКО в `apps/web/app.py` через `include_router`

### 3. Шаблоны Jinja2
```python
# ❌ НЕПРАВИЛЬНО
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

# ✅ ПРАВИЛЬНО
from apps.web.jinja import templates  # Единый шаблонизатор
```

### 4. Сессии БД
```python
# ❌ НЕПРАВИЛЬНО в веб-роутах
async with get_async_session() as session:
    result = await repo.get(session, id)

# ✅ ПРАВИЛЬНО
@router.get("/")
async def route(session: AsyncSession = Depends(get_db_session)):
    result = await repo.get(session, id)
```

### 5. URLHelper
```python
# ❌ НЕПРАВИЛЬНО
redirect_url = "https://staffprobot.ru/owner/objects"

# ✅ ПРАВИЛЬНО
from core.utils.url_helper import URLHelper
redirect_url = URLHelper.get_web_url("/owner/objects")
```

### 6. Docker перезапуск
- `apps/web/*` → `docker compose -f docker-compose.dev.yml restart web`
- `apps/bot/*` → `docker compose -f docker-compose.dev.yml restart bot`
- `shared/*` или `domain/*` → `docker compose -f docker-compose.dev.yml restart web bot celery_worker celery_beat`

## ПЕРЕД ЛЮБЫМ ИЗМЕНЕНИЕМ

1. Проверить через `grep` или `codebase_search` существующий код
2. При сомнениях - спросить Project Brain: http://192.168.2.107:8003/chat
3. Прочитать соответствующие правила из `.cursor/rules/`:
   - `brainrules.mdc` - общие правила разработки
   - `workflow.mdc` - процесс выполнения задач
   - `conventions.mdc` - стиль кода
   - `user_id_handling.mdc` - правила работы с user_id

## ПОСЛЕ ИЗМЕНЕНИЙ

1. Проверить `read_lints` на ошибки
2. Предложить команду перезапуска контейнеров
3. Напомнить об обновлении `doc/plans/roadmap.md`
4. Предложить команды для тестирования

## ПРИМЕРЫ ПРОВЕРОК

### Проверка роутов
```python
# Проверить, что нет дублирующих роутов
# Проверить префикс роли в app.py
# Проверить использование Depends(get_db_session)
```

### Проверка user_id
```python
# Найти все использования current_user.get("id")
# Убедиться, что везде используется get_user_id_from_current_user
```

### Проверка шаблонов
```python
# Убедиться, что используется apps.web.jinja.templates
# Проверить использование static_version для статики
```
