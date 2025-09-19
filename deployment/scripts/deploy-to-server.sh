#!/bin/bash
# Скрипт развертывания StaffProBot на сервере

set -e

echo "🚀 Развертывание StaffProBot на сервере..."

# 1. Обновляем код
echo "📥 Обновление кода из Git..."
git pull origin main

# 2. Создаем .env.prod если его нет
if [ ! -f .env.prod ]; then
    echo "📝 Создание .env.prod..."
    cat > .env.prod << 'EOF'
APP_NAME=StaffProBot_Prod
ENVIRONMENT=production
DEBUG=false

DATABASE_URL=postgresql://postgres:prod_password_123@postgres:5432/staffprobot_prod
POSTGRES_DB=staffprobot_prod
POSTGRES_USER=postgres
POSTGRES_PASSWORD=prod_password_123

REDIS_URL=redis://:prod_redis_pass_456@redis:6379
REDIS_PASSWORD=prod_redis_pass_456

RABBITMQ_URL=amqp://prod_admin:prod_password@rabbitmq:5672
RABBITMQ_USER=prod_admin
RABBITMQ_PASSWORD=prod_password

TELEGRAM_BOT_TOKEN=your_prod_bot_token_here
OPENAI_API_KEY=your_prod_openai_api_key_here
SECRET_KEY=your_prod_secret_key_here

MAX_DISTANCE_METERS=500
LOCATION_ACCURACY_METERS=50

GRAFANA_USER=prod_admin
GRAFANA_PASSWORD=prod_admin_pass

# Дополнительные переменные для продакшена
TELEGRAM_WEBHOOK_URL=https://bot.staffprobot.ru
EOF
    echo "⚠️  ВАЖНО: Отредактируйте .env.prod и установите реальные токены!"
fi

# 3. Останавливаем старые контейнеры
echo "🛑 Остановка старых контейнеров..."
docker compose -f docker-compose.prod.yml --env-file .env.prod down || true

# 4. Собираем образы
echo "🔨 Сборка Docker образов..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache

# 5. Запускаем сервисы
echo "🚀 Запуск сервисов..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 6. Ждем готовности сервисов
echo "⏳ Ожидание готовности сервисов..."
sleep 30

# 7. Проверяем статус
echo "📊 Статус сервисов:"
docker compose -f docker-compose.prod.yml --env-file .env.prod ps

# 8. Проверяем health endpoints
echo "🔍 Проверка health endpoints..."
echo "Веб-сервис:"
curl -s http://localhost:8001/health || echo "❌ Веб-сервис недоступен"

echo "✅ Развертывание завершено!"
echo "🌐 Веб-интерфейс: http://localhost:8001"
echo "📊 Мониторинг: http://localhost:3001 (Grafana)"
