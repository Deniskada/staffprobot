# Technical Context: StaffProBot

## Backend Stack
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Validation**: Pydantic

## База данных
- **PostgreSQL**: Основная БД
- **Redis**: Кэш и сессии
- **RabbitMQ**: Очереди сообщений

## Инфраструктура
- **Docker**: Контейнеризация
- **Docker Compose**: Оркестрация для dev/prod
- **Nginx**: Reverse proxy (общий контейнер `sites_nginx` на проде)
- **SSL**: Let's Encrypt (общий `sites_certbot`)
- **Production**: `155.212.217.38`, путь `/opt/sites/staffprobot`
- **Dev**: `192.168.77.177`, доступ через `dev.staffprobot.ru`

## Медиа-хранилище (S3)
- **Абстракция**: `shared/services/media_storage/base.py` → `MediaStorageClient` (ABC)
- **S3-клиент**: `shared/services/media_storage/s3_client.py` → `S3MediaStorageClient` (MinIO / S3-совместимый)
- **Telegram-клиент**: `shared/services/media_storage/telegram_client.py` → `TelegramMediaStorageClient`
- **Фабрика**: `shared/services/media_storage/factory.py` → `get_media_storage_client(provider_override)`
- **Оркестратор**: `shared/services/media_orchestrator.py` → `MediaOrchestrator` (Redis-backed потоки медиа)
- **Dev**: MinIO (Docker), env: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- **Prod**: MinIO (Docker на VPS), env: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- **Провайдер**: `MEDIA_STORAGE_PROVIDER` = `telegram` | `minio` | `s3`
- **Режимы хранения**: `telegram` / `storage` / `both` (настройка владельца)
- **URL**: через прокси `/api/media/{key}` (не presigned, безопасный доступ)

## Интеграции
- **Telegram Bot API**: aiogram
- **OpenAI**: GPT для аналитики
- **YooKassa**: Платежи
- **Яндекс Карты**: Геолокация

## Мониторинг
- **Prometheus**: Метрики
- **Grafana**: Визуализация
- **Логирование**: Структурированные логи (JSON)

## Разработка
- **Git**: Версионирование
- **Testing**: pytest
- **Code Quality**: Линтеры и форматтеры
- **Documentation**: Markdown в `doc/`
