# StaffProBot - Patterns & Practices

## Критические паттерны

### 1. user_id vs telegram_id
**Проблема**: Путаница между внутренним ID и telegram_id  
**Решение**: Всегда использовать `get_user_id_from_current_user()`

```python
# ❌ НЕПРАВИЛЬНО
user_id = current_user.get("id")  # Это telegram_id!

# ✅ ПРАВИЛЬНО
from shared.services.user_service import get_user_id_from_current_user
user_id = await get_user_id_from_current_user(current_user, session)
```

### 2. Роутинг с префиксами ролей
**Проблема**: Дублирование префиксов, конфликты роутов  
**Решение**: Префикс только в `app.py`, без префикса в файлах роутов

```python
# apps/web/routes/owner/objects.py
router = APIRouter()  # БЕЗ prefix!

@router.get("/")  # Будет /owner/ после include_router
async def list_objects():
    pass

# apps/web/app.py
app.include_router(
    objects.router,
    prefix="/owner",  # Префикс ТОЛЬКО здесь!
    tags=["owner"]
)
```

### 3. Единый шаблонизатор
**Проблема**: Дублирование Jinja2Templates  
**Решение**: Использовать единый шаблонизатор

```python
# ❌ НЕПРАВИЛЬНО
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

# ✅ ПРАВИЛЬНО
from apps.web.jinja import templates  # Единый шаблонизатор
```

### 4. Сессии БД в веб-роутах
**Проблема**: Использование `async with get_async_session()`  
**Решение**: Только `Depends(get_db_session)`

```python
# ❌ НЕПРАВИЛЬНО
async with get_async_session() as session:
    result = await repo.get(session, id)

# ✅ ПРАВИЛЬНО
@router.get("/")
async def route(session: AsyncSession = Depends(get_db_session)):
    result = await repo.get(session, id)
```

### 5. URLHelper вместо хардкода
**Проблема**: Хардкод доменов в коде  
**Решение**: Использовать URLHelper

```python
# ❌ НЕПРАВИЛЬНО
redirect_url = "https://staffprobot.ru/owner/objects"

# ✅ ПРАВИЛЬНО
from core.utils.url_helper import URLHelper
redirect_url = URLHelper.get_web_url("/owner/objects")
```

## Архитектурные паттерны

### Dependency Injection
```python
from apps.web.dependencies import (
    get_current_user,
    require_owner_or_superadmin,
    get_db_session
)

@router.get("/")
async def route(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    pass
```

### Структурированное логирование
```python
from core.logging.logger import logger

logger.info(
    "Shift opened successfully",
    user_id=user_id,
    shift_id=shift_id,
    object_id=object_id,
    coordinates=coordinates
)
```

### Обработка ошибок
```python
try:
    user = await user_service.create_user(data)
except ValidationError as e:
    logger.error("User validation failed", user_data=data, error=str(e))
    raise
except DatabaseError as e:
    logger.error("Database error", error=str(e))
    raise UserCreationError("Failed to create user")
```

## SQLAlchemy 2.0 паттерны

### Async запросы
```python
from sqlalchemy import select

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

### Bulk операции
```python
# Для массовых операций использовать bulk методы
await session.execute(
    update(User).where(User.role == "employee").values(status="active")
)
```

## Тестирование паттерны

### Unit тесты
```python
async def test_create_user_with_valid_data():
    # Arrange
    user_data = {"name": "Test", "email": "test@test.com"}
    
    # Act
    user = await user_service.create_user(user_data)
    
    # Assert
    assert user.name == "Test"
```

### Integration тесты
```python
async def test_route_requires_authentication(client):
    response = await client.get("/owner/objects")
    assert response.status_code == 401
```

## Workflow паттерны

### Согласование перед реализацией
1. Предложить решение с примерами кода
2. Объяснить архитектурные решения
3. Дождаться подтверждения
4. Реализовать после подтверждения

### Обновление roadmap после задачи
1. Отметить задачу как выполненную [x]
2. Обновить прогресс в шапке
3. Добавить Type, Files, Acceptance критерии
4. Создать коммит на русском

---

**Источники**: `.cursor/rules/brainrules.mdc`, `.cursor/rules/conventions.mdc`, `.cursor/rules/workflow.mdc`
