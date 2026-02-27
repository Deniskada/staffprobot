# System Patterns: StaffProBot

## Архитектурные решения

### Domain-Driven Design (DDD)
- **Domain**: Бизнес-логика и сущности (`domain/entities/`)
- **Shared**: Общие сервисы и утилиты (`shared/services/`)
- **Apps**: Приложения (bot, web, api, analytics)

### Работа с данными
- Использование SQLAlchemy ORM для работы с БД
- Сессии через `Depends(get_db_session)` в FastAPI
- Кэширование через Redis для часто используемых данных

### API Design
- RESTful API для веб-интерфейса
- WebSocket для real-time обновлений (если нужно)
- Telegram Bot API для бота

### Аутентификация и авторизация
- JWT токены для веб-интерфейса
- Telegram user_id для бота
- Роли: owner, manager, employee

## Паттерны кода

### Обработка ошибок
- Использование try/except с логированием
- Структурированное логирование (JSON)
- Обработка ошибок через FastAPI exception handlers

### Именование
- Python naming conventions (snake_case)
- Типизация через type hints
- Документация через docstrings

### Тестирование
- Unit тесты в `tests/unit/`
- Integration тесты в `tests/integration/`
- Performance тесты в `tests/performance/`

---

**Использование**: Документируйте архитектурные решения и паттерны при работе через `/creative` или `/plan`
