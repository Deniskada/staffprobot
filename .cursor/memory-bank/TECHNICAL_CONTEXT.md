# StaffProBot - Technical Context

## Технологический стек

### Backend
- **Python**: 3.11+
- **FastAPI**: Асинхронный веб-фреймворк
- **SQLAlchemy**: 2.0 (async синтаксис)
- **Alembic**: Миграции БД
- **Pydantic**: Валидация данных

### Database
- **PostgreSQL**: 15+ с расширением PostGIS
- **Redis**: Кэш и очереди
- **RabbitMQ**: Message broker для Celery

### Bot
- **Aiogram**: 3.x для Telegram бота
- **Async**: Все операции асинхронные

### Frontend
- **Jinja2**: Шаблонизация
- **JavaScript**: Vanilla (без фреймворков)
- **CSS**: Кастомные стили

### Deployment
- **Docker Compose**: Оркестрация контейнеров
- **Nginx**: Reverse proxy (на проде)
- **SSL**: Автоматическое обновление сертификатов

## Переменные окружения

### База данных
- `DB_NAME`: `staffprobot_dev` (dev) или `staffprobot_prod` (prod)
- `DB_USER`: `postgres`
- `DB_PASSWORD`: Из `.env` файла
- `DB_HOST`: `postgres` (внутри Docker сети)

### API ключи
- `TELEGRAM_BOT_TOKEN`: Токен Telegram бота
- `ANTHROPIC_API_KEY`: Для Claude (если используется)
- `OPENAI_API_KEY`: Для OpenAI (если используется)

### Другие
- `ENVIRONMENT`: `dev` или `prod`
- `REDIS_URL`: URL для подключения к Redis
- `RABBITMQ_URL`: URL для подключения к RabbitMQ

## Docker команды

### Dev окружение
```bash
# Запуск
docker compose -f docker-compose.dev.yml up -d

# Остановка
docker compose -f docker-compose.dev.yml down

# Логи
docker compose -f docker-compose.dev.yml logs web --tail 50

# Выполнение команды
docker compose -f docker-compose.dev.yml exec web python -c "код"

# База данных
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev
```

### Prod окружение
```bash
# Подключение
ssh staffprobot@staffprobot.ru

# Обновление кода
cd /opt/staffprobot && git fetch origin && git checkout main && git pull origin main

# Перезапуск
docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d

# База данных
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod
```

## Инструменты разработки

### Project Brain
- **URL**: http://192.168.2.107:8003/chat
- **API**: `POST http://192.168.2.107:8003/api/query`
- **Назначение**: Вопросы по коду, архитектуре, логике

### Supercode.sh
- **Назначение**: Workflows и режимы для AI
- **Режимы**: StaffPro Architect, Roadmap Executor, Refactor & Review
- **Workflows**: Новая задача из roadmap, Проверка правок в routes, и т.д.

### Memory Bank
- **Назначение**: Сохранение контекста между сессиями
- **Структура**: `.cursor/memory-bank/`

### OpenSpec / spec-kit
- **Назначение**: Spec-driven разработка
- **Структура**: `specs/capabilities/`, `changes/`

### TaskMaster
- **Назначение**: Управление задачами через MCP
- **Интеграция**: С roadmap.md и Supercode workflows

## Тестирование

### Unit тесты
```bash
docker compose -f docker-compose.dev.yml exec web pytest tests/unit
```

### Integration тесты
```bash
docker compose -f docker-compose.dev.yml exec web pytest tests/integration
```

### Покрытие
```bash
docker compose -f docker-compose.dev.yml exec web \
  pytest --cov=apps --cov=core --cov-report=html
```

## Миграции БД

### Создание миграции
```bash
docker compose -f docker-compose.dev.yml exec web \
  alembic revision --autogenerate -m "описание изменений"
```

### Применение миграций
```bash
docker compose -f docker-compose.dev.yml exec web alembic upgrade head
```

### Откат миграции
```bash
docker compose -f docker-compose.dev.yml exec web alembic downgrade -1
```

## Мониторинг и логи

### Логи веб-приложения
```bash
docker compose -f docker-compose.dev.yml logs web --tail 100 -f
```

### Логи бота
```bash
docker compose -f docker-compose.dev.yml logs bot --tail 100 -f
```

### Логи Celery
```bash
docker compose -f docker-compose.dev.yml logs celery_worker --tail 100 -f
```

## Производительность

### Оптимизация запросов
- Использование индексов для часто используемых полей
- Избегание N+1 проблем через eager loading
- Bulk операции для массовых данных

### Кэширование
- Redis для кэширования объектов и пользователей
- Агрессивное кэширование статики с версионированием
- Инвалидация кэша при изменении данных

---

**Последнее обновление**: 2026-02-04
