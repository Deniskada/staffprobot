# 🐳 Docker-разработка StaffProBot

## Обзор

Этот документ описывает, как запустить StaffProBot в Docker контейнерах для разработки и продакшена. Docker обеспечивает кросс-платформенность и избавляет от проблем с установкой зависимостей.

## 🚀 Быстрый старт

### Предварительные требования

- **Docker Desktop** (Windows/macOS) или **Docker Engine** (Linux)
- **Docker Compose** (обычно включен в Docker Desktop)
  - Старая версия: `docker-compose` (v1)
  - Новая версия: `docker compose` (v2) - встроена в Docker

### Запуск в режиме разработки

#### Linux/macOS
```bash
chmod +x scripts/docker-dev.sh
./scripts/docker-dev.sh
```

#### Windows
```cmd
scripts\docker-dev.bat
```

#### Ручной запуск
```bash
# Создание .env файла
cp env.example .env
# Редактирование .env файла с вашими токенами

# Запуск
docker-compose -f docker-compose.dev.yml up --build -d
```

## 📁 Структура Docker файлов

```
docker/
├── Dockerfile          # Продакшен образ
├── Dockerfile.dev      # Образ для разработки
└── monitoring/         # Конфигурация мониторинга

docker-compose.yml      # Основной compose (продакшен)
docker-compose.dev.yml  # Compose для разработки
docker-compose.prod.yml # Compose для продакшена
.dockerignore           # Исключения для Docker
```

## 🔧 Режим разработки

### Особенности dev режима

- **Hot-reload**: Изменения кода отражаются без перезапуска
- **Отладочные порты**: Все сервисы доступны локально
- **Тестовые данные**: Отдельная база данных для разработки
- **Логирование**: Подробные логи для отладки

### Переменные окружения

Создайте `.env` файл на основе `env.example`:

```bash
# Основные настройки
ENVIRONMENT=development
DEBUG=true

# База данных
DATABASE_URL=postgresql://postgres:password@postgres:5432/staffprobot_dev

# Telegram
TELEGRAM_BOT_TOKEN_PROD=your_prod_bot_token_here
TELEGRAM_BOT_TOKEN_DEV=

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
```

### Доступные сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| Bot | 8000 | Основное приложение |
| PostgreSQL | 5432 | База данных |
| Redis | 6379 | Кэширование |
| RabbitMQ | 5672 | Очереди сообщений |
| RabbitMQ UI | 15672 | Управление RabbitMQ |
| Prometheus | 9090 | Метрики |
| Grafana | 3000 | Дашборды |

## 🚀 Продакшен режим

### Запуск продакшена (с авто-миграциями)

```bash
# Создание .env
cp env.example .env
# Заполните POSTGRES_DB/USER/PASSWORD, SECRET_KEY, TELEGRAM_BOT_TOKEN_PROD, REDIS_PASSWORD и т.д.

# Сборка и запуск: база/брокеры → миграции → приложения
docker compose -f docker-compose.prod.yml up -d postgres redis rabbitmq
docker compose -f docker-compose.prod.yml run --rm migrator
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d web bot celery_worker celery_beat prometheus grafana backup
```

### Override для web (команда и порт)

Чтобы не редактировать основной compose, используем `docker-compose.prod.override.yml`:

```yaml
services:
  web:
    command: python -m uvicorn apps.web.app:app --host 0.0.0.0 --port 8000
    ports:
      - "127.0.0.1:8000:8000"
```

Запуск с учётом override:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d web
```

### Особенности продакшена

- **Безопасность**: Непривилегированный пользователь
- **Оптимизация**: Минимальный размер образа
- **Мониторинг**: Health checks и метрики
- **Автоперезапуск**: `restart: unless-stopped`
- **Авто-миграции**: отдельный сервис `migrator` выполняет `alembic upgrade head`

### Чек-лист продакшн-деплоя

1. Обновить код: `git pull --ff-only` или `rsync` на сервер
2. Проверить `.env` (POSTGRES_*, SECRET_KEY, TELEGRAM_BOT_TOKEN_PROD, REDIS_PASSWORD)
3. Поднять базы и брокеры: `docker compose -f docker-compose.prod.yml up -d postgres redis rabbitmq`
4. Прогнать миграции: `docker compose -f docker-compose.prod.yml run --rm migrator`
5. Запуск приложений: `docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d web bot celery_worker celery_beat`
6. Проверить: `curl http://127.0.0.1:8000/health`
7. Nginx (если используется): `sudo nginx -t && sudo systemctl reload nginx`
### Полезные команды продакшена

```bash
# Прогнать миграции повторно
docker compose -f docker-compose.prod.yml run --rm migrator

# Проверить состояние Alembic
docker compose -f docker-compose.prod.yml exec -T web alembic current | cat
```

## 🛠️ Полезные команды

### Управление контейнерами

```bash
# Просмотр логов
docker-compose -f docker-compose.dev.yml logs -f bot

# Остановка
docker-compose -f docker-compose.dev.yml down

# Перезапуск сервиса
docker-compose -f docker-compose.dev.yml restart bot

# Просмотр статуса
docker-compose -f docker-compose.dev.yml ps
```

### Работа с базой данных

```bash
# Подключение к PostgreSQL
docker exec -it staffprobot_postgres_dev psql -U postgres -d staffprobot_dev

# Создание миграции
docker exec -it staffprobot_bot_dev python -m alembic revision --autogenerate -m "description"

# Применение миграций
docker exec -it staffprobot_bot_dev python -m alembic upgrade head
```

### Тестирование

```bash
# Запуск тестов
docker exec -it staffprobot_bot_dev python -m pytest tests/

# Запуск с покрытием
docker exec -it staffprobot_bot_dev python -m pytest tests/ --cov=apps --cov-report=html
```

## 🔍 Отладка

### Просмотр логов

```bash
# Все сервисы
docker-compose -f docker-compose.dev.yml logs

# Конкретный сервис
docker-compose -f docker-compose.dev.yml logs -f bot

# Последние 100 строк
docker-compose -f docker-compose.dev.yml logs --tail=100 bot
```

### Вход в контейнер

```bash
# Вход в контейнер бота
docker exec -it staffprobot_bot_dev bash

# Вход в PostgreSQL
docker exec -it staffprobot_postgres_dev psql -U postgres -d staffprobot_dev
```

### Проверка здоровья

```bash
# Статус всех сервисов
docker-compose -f docker-compose.dev.yml ps

# Проверка health checks
docker inspect staffprobot_postgres_dev | grep -A 10 Health
```

## 🐛 Решение проблем

### Частые проблемы

#### 1. Порт уже занят
```bash
# Поиск процесса на порту
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Остановка всех контейнеров
docker-compose -f docker-compose.dev.yml down
```

#### 2. Проблемы с правами доступа
```bash
# Очистка volumes
docker-compose -f docker-compose.dev.yml down -v

# Пересборка образов
docker-compose -f docker-compose.dev.yml build --no-cache
```

#### 3. Проблемы с базой данных
```bash
# Сброс базы данных
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d postgres

# Проверка подключения
docker exec -it staffprobot_postgres_dev pg_isready -U postgres
```

### Очистка

```bash
# Остановка и удаление контейнеров
docker-compose -f docker-compose.dev.yml down

# Удаление образов
docker rmi staffprobot_bot_dev

# Очистка неиспользуемых ресурсов
docker system prune -f
```

## 📚 Дополнительные ресурсы

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostGIS Docker](https://postgis.net/install/)
- [Redis Docker](https://hub.docker.com/_/redis)

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose -f docker-compose.dev.yml logs`
2. Убедитесь, что Docker запущен
3. Проверьте, что порты не заняты
4. Создайте issue в репозитории проекта
