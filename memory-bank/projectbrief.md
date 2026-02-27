# Project Brief: StaffProBot

## Проект
Система управления персоналом и сменами для бизнеса с Telegram-ботом и веб-интерфейсом.

## Основные компоненты
- **Backend**: FastAPI (Python)
- **База данных**: PostgreSQL
- **Кэш**: Redis
- **Очереди**: RabbitMQ + Celery
- **Telegram Bot**: aiogram
- **Веб-интерфейс**: FastAPI + Jinja2 templates
- **Мониторинг**: Prometheus + Grafana

## Архитектура
- **DDD**: Domain-Driven Design с разделением на domain, shared, apps
- **Микросервисы**: Bot, Web, API, Analytics, Scheduler
- **Docker**: Docker Compose для разработки и продакшена
- **CI/CD**: Автоматический деплой через скрипты

## Технологический стек
- Python 3.11+
- FastAPI
- PostgreSQL
- Redis
- RabbitMQ
- Celery
- aiogram (Telegram Bot)
- SQLAlchemy
- Alembic (миграции)
- Pydantic
- Prometheus
- Grafana

## Инфраструктура

### Production
- **Сервер**: `155.212.217.38` (VPS)
- **Путь**: `/opt/sites/staffprobot`
- **URL**: https://staffprobot.ru
- **Nginx**: общий `sites_nginx`, SSL через `sites_certbot`

### Dev
- **Сервер**: `192.168.77.177` (локальный)
- **URL**: https://dev.staffprobot.ru (через `79.174.62.232`)
- **Прокси**: `dev-proxy` → `staffprobot_web_dev:8001`

### Домены
- `staffprobot.ru`, `www.staffprobot.ru` → `155.212.217.38`
- `dev.staffprobot.ru` → `79.174.62.232` → `192.168.77.177`
