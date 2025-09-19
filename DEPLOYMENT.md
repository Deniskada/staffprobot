# 🚀 Развертывание StaffProBot на сервере

## Быстрый старт

### 1. На сервере
```bash
# Клонируем репозиторий (если еще не клонирован)
git clone https://github.com/Deniskada/staffprobot.git
cd staffprobot

# Или обновляем существующий
git pull origin main

# Запускаем автоматическое развертывание
./deployment/scripts/deploy-to-server.sh
```

### 2. Настройка токенов
После первого запуска отредактируйте `.env.prod`:
```bash
nano .env.prod
```

Установите реальные значения:
- `TELEGRAM_BOT_TOKEN` - токен бота от @BotFather
- `OPENAI_API_KEY` - ключ OpenAI API
- `SECRET_KEY` - секретный ключ для JWT

### 3. Перезапуск с новыми токенами
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod restart bot web
```

## Ручное развертывание

### 1. Обновление кода
```bash
git pull origin main
```

### 2. Сборка образов
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
```

### 3. Запуск сервисов
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

### 4. Проверка статуса
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

## Полезные команды

### Логи сервисов
```bash
# Все сервисы
docker compose -f docker-compose.prod.yml --env-file .env.prod logs

# Конкретный сервис
docker compose -f docker-compose.prod.yml --env-file .env.prod logs bot
docker compose -f docker-compose.prod.yml --env-file .env.prod logs web
```

### Перезапуск сервисов
```bash
# Все сервисы
docker compose -f docker-compose.prod.yml --env-file .env.prod restart

# Конкретный сервис
docker compose -f docker-compose.prod.yml --env-file .env.prod restart bot
```

### Остановка
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

## Проверка работоспособности

### Health endpoints
```bash
# Веб-сервис
curl http://localhost:8001/health

# Ожидаемый ответ: {"status": "healthy", "service": "web"}
```

### Статус контейнеров
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

Все сервисы должны иметь статус `Up` и `healthy`.

## Порты

- **8001** - Веб-интерфейс
- **3001** - Grafana (мониторинг)
- **9091** - Prometheus (метрики)
- **5433** - PostgreSQL (внешний доступ)
- **6380** - Redis (внешний доступ)
- **5673** - RabbitMQ (внешний доступ)
- **15673** - RabbitMQ Management (внешний доступ)

## Troubleshooting

### Проблема: Бот не запускается
1. Проверьте токен в `.env.prod`
2. Проверьте логи: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs bot`

### Проблема: Веб-сервис недоступен
1. Проверьте порт 8001
2. Проверьте логи: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs web`

### Проблема: База данных недоступна
1. Проверьте пароли в `.env.prod`
2. Проверьте логи: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs postgres`
