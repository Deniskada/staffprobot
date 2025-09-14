#!/bin/bash
# Скрипт проверки здоровья сервисов StaffProBot

set -e

echo "🏥 Checking service health..."

# Проверка Docker контейнеров
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "❌ Some containers are not running"
    exit 1
fi

# Проверка HTTP endpoints
if ! curl -f -s https://staffprobot.ru/health > /dev/null; then
    echo "❌ Main site is not responding"
    exit 1
fi

if ! curl -f -s https://api.staffprobot.ru/health > /dev/null; then
    echo "❌ API is not responding"
    exit 1
fi

echo "✅ All services are healthy"
