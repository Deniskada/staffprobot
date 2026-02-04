# StaffProBot - System Architecture

## Слоистая архитектура (DDD + CQRS)

```
apps/
  web/              # FastAPI web interface
    routes/         # API endpoints (owner/manager/employee/admin)
    services/       # Бизнес-логика
    templates/      # Jinja2 шаблоны
  bot/              # Telegram bot
    handlers/       # Обработчики команд
    services/       # Бизнес-логика бота
core/
  auth/             # Аутентификация (user_manager.py)
  database/         # SQLAlchemy (async)
  logging/          # Структурированное логирование
  geolocation/       # Расчёт расстояний
domain/
  entities/         # Модели БД (User, Object, Shift, etc)
shared/
  services/         # Общая бизнес-логика
  templates/        # Общие шаблоны
```

## Ключевые принципы

### Domain-Driven Design
- Разделение кода по бизнес-доменам
- Слоистая архитектура: domain → infrastructure → application
- Моделирование бизнес-сущностей как объектов

### CQRS
- Разделение операций чтения и записи
- Оптимизация моделей для конкретных сценариев
- Отдельные схемы для команд и запросов

### Микросервисы
- Каждый сервис независим (web + bot + celery)
- Асинхронная коммуникация через события
- Минимизация межсервисных зависимостей

### Async/Await
- Для всех I/O операций
- Connection pooling для БД
- Неблокирующие операции

## Docker архитектура

### Контейнеры
- `web` - FastAPI приложение
- `bot` - Telegram бот
- `celery_worker` - Celery worker (фоновые задачи)
- `celery_beat` - Celery scheduler (расписание)
- `postgres` - PostgreSQL + PostGIS
- `redis` - Кэш и очереди
- `rabbitmq` - Message broker

### Правила перезапуска
- `apps/web/*` → `restart web`
- `apps/bot/*` → `restart bot`
- `core/celery/tasks/*` → `restart celery_worker celery_beat`
- `shared/*` или `domain/*` → `restart web bot celery_worker celery_beat`

## База данных

### Основные таблицы
- `users` - пользователи (telegram_id + role)
- `objects` - объекты работы (адрес + координаты)
- `shifts` - смены (user + object + время)
- `contracts` - договоры (user + conditions)
- `timesheets` - табели (расчёты по сменам)
- `contract_templates` - шаблоны договоров
- `constructor_flows` - потоки конструктора
- `constructor_steps` - шаги конструктора

### Индексы
- GIST индексы для координат (PostGIS)
- Индексы для часто используемых полей
- Составные индексы для запросов

## Геолокация

### Использование PostGIS
- Хранение координат в формате PostGIS
- Расчёт расстояний через PostGIS функции
- GIST индексы для быстрого поиска

### Валидация
- Проверка координат перед сохранением
- Проверка расстояния до объекта при открытии смены

## Кэширование

### Redis
- Кэш объектов и пользователей
- Сессии пользователей
- Временные данные

### Стратегия кэширования
- Агрессивное кэширование статики (max-age=31536000)
- Версионирование статики через `static_version` фильтр
- Инвалидация кэша при изменении данных

---

**Последнее обновление**: 2026-02-04
