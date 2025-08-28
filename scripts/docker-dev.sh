#!/bin/bash

# Скрипт для запуска StaffProBot в режиме разработки
echo "🚀 Запуск StaffProBot в режиме разработки..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверка Docker Compose (поддержка обеих версий)
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

echo "✅ Используется: $DOCKER_COMPOSE_CMD"

# Переход в корневую директорию проекта
cd "$(dirname "$0")/.."

# Создание .env файла если его нет
if [ ! -f .env ]; then
    echo "📝 Создание .env файла из примера..."
    cp env.example .env
    echo "⚠️  Отредактируйте .env файл, указав ваши токены и настройки"
fi

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
$DOCKER_COMPOSE_CMD -f docker-compose.dev.yml down

# Сборка и запуск
echo "🔨 Сборка и запуск контейнеров..."
$DOCKER_COMPOSE_CMD -f docker-compose.dev.yml up --build -d

# Ожидание готовности сервисов
echo "⏳ Ожидание готовности сервисов..."
sleep 10

# Проверка статуса
echo "📊 Статус сервисов:"
$DOCKER_COMPOSE_CMD -f docker-compose.dev.yml ps

echo "✅ StaffProBot запущен в режиме разработки!"
echo "🌐 Бот доступен на порту 8000"
echo "🗄️  База данных PostgreSQL на порту 5432"
echo "🔴 Redis на порту 6379"
echo "🐰 RabbitMQ на порту 5672 (управление: http://localhost:15672)"
echo "📈 Prometheus на порту 9090"
echo "📊 Grafana на порту 3000"

echo ""
echo "📝 Полезные команды:"
echo "  Просмотр логов: $DOCKER_COMPOSE_CMD -f docker-compose.dev.yml logs -f bot"
echo "  Остановка: $DOCKER_COMPOSE_CMD -f docker-compose.dev.yml down"
echo "  Перезапуск: $DOCKER_COMPOSE_CMD -f docker-compose.dev.yml restart bot"
