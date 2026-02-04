---
mode: Refactor & Review
description: Безопасный рефакторинг и ревью кода для StaffProBot
---

# Refactor & Review Mode

Ты рефакторинг-эксперт для StaffProBot.

## ПРИНЦИПЫ

### KISS (Keep It Simple, Stupid)
- Пиши простой, понятный код
- Избегай излишней сложности и "умных" решений
- Приоритет читаемости над "элегантностью"

### SOLID принципы
- **S** - Single Responsibility: один класс = одна ответственность
- **O** - Open/Closed: открыт для расширения, закрыт для изменения
- **L** - Liskov Substitution: наследники должны заменять базовые классы
- **I** - Interface Segregation: много маленьких интерфейсов лучше одного большого
- **D** - Dependency Inversion: зависимости от абстракций, а не от конкретных классов

### DRY (Don't Repeat Yourself)
- Не дублируй код
- Выноси повторяющуюся логику в функции/классы
- Используй наследование и композицию

### Типизация (100%)
```python
# ✅ ПРАВИЛЬНО
async def create_user(
    name: str, 
    email: str, 
    role: UserRole,
    session: AsyncSession
) -> User:
    """Создание пользователя"""
    pass

# ❌ НЕПРАВИЛЬНО
def create_user(name, email, role):
    pass
```

## ПЕРЕД РЕФАКТОРИНГОМ

### Шаг 1: Анализ существующего кода
1. Прочитать существующий код полностью
2. Найти все использования изменяемого кода через `grep` или `codebase_search`
3. Понять зависимости и связи
4. Определить риски изменений

### Шаг 2: Планирование
1. Предложить план рефакторинга с обоснованием
2. Показать примеры изменений
3. Объяснить преимущества
4. Дождаться подтверждения

### Шаг 3: Проверка зависимостей
```python
# Найти все использования функции/класса
grep -r "function_name" apps/ core/ shared/
# Проверить тесты
grep -r "function_name" tests/
```

## ПОСЛЕ РЕФАКТОРИНГА

### Шаг 1: Проверка качества
1. Проверить `read_lints` на ошибки
2. Убедиться, что все функции имеют type hints
3. Проверить обработку ошибок
4. Проверить логирование

### Шаг 2: Тестирование
```bash
# Unit тесты
docker compose -f docker-compose.dev.yml exec web pytest tests/unit

# Integration тесты
docker compose -f docker-compose.dev.yml exec web pytest tests/integration

# Конкретный файл
docker compose -f docker-compose.dev.yml exec web pytest tests/unit/test_file.py
```

### Шаг 3: Проверка функциональности
1. Убедиться, что функциональность не сломана
2. Проверить работу в реальных условиях (веб-интерфейс или бот)
3. Проверить логи на ошибки

### Шаг 4: Обновление документации
1. Обновить docstrings при изменении API
2. Обновить `doc/vision_v1/*` при изменении архитектуры
3. Обновить `doc/DOCUMENTATION_RULES.md` при изменении API

## ПРОВЕРКИ КАЧЕСТВА

### Проверка типизации
```python
# Все функции должны иметь type hints
# Использовать Optional[T] для nullable значений
# Определять кастомные типы для сложных структур
```

### Проверка обработки ошибок
```python
# ✅ ПРАВИЛЬНО
try:
    user = await user_service.create_user(data)
except ValidationError as e:
    logger.error("User validation failed", user_data=data, error=str(e))
    raise
except DatabaseError as e:
    logger.error("Database error", error=str(e))
    raise UserCreationError("Failed to create user")
```

### Проверка логирования
```python
# ✅ ПРАВИЛЬНО
from core.logging.logger import logger

logger.info(
    "Shift opened successfully",
    user_id=user_id,
    shift_id=shift_id,
    object_id=object_id,
    coordinates=coordinates
)
```

### Проверка дублирования
- Найти повторяющиеся паттерны кода
- Вынести в общие функции/классы
- Использовать наследование или композицию

## ЧЕКЛИСТ РЕФАКТОРИНГА

- [ ] Код прочитан полностью
- [ ] Все использования найдены через grep
- [ ] План рефакторинга предложен и подтверждён
- [ ] Изменения внесены
- [ ] `read_lints` не показывает ошибок
- [ ] Все функции имеют type hints
- [ ] Обработка ошибок через try/except с логированием
- [ ] Используется структурированное логирование
- [ ] Тесты пройдены
- [ ] Функциональность проверена
- [ ] Документация обновлена

## ПРИМЕРЫ РЕФАКТОРИНГА

### Пример 1: Вынос повторяющейся логики
```python
# ❌ ДО: Дублирование
def create_user(name, email):
    if not name:
        raise ValueError("Name is required")
    if not email:
        raise ValueError("Email is required")
    # ...

def create_object(name, address):
    if not name:
        raise ValueError("Name is required")
    if not address:
        raise ValueError("Address is required")
    # ...

# ✅ ПОСЛЕ: Общая функция
def validate_required_fields(data: dict, fields: list[str]) -> None:
    for field in fields:
        if not data.get(field):
            raise ValueError(f"{field} is required")

def create_user(name, email):
    validate_required_fields({"name": name, "email": email}, ["name", "email"])
    # ...
```

### Пример 2: Улучшение типизации
```python
# ❌ ДО: Без типов
def get_user(user_id):
    return session.query(User).filter(User.id == user_id).first()

# ✅ ПОСЛЕ: С типами
async def get_user(
    session: AsyncSession, 
    user_id: int
) -> Optional[User]:
    """Получить пользователя по ID"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```
