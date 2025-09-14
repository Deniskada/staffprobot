#!/bin/bash
# Скрипт деплоя StaffProBot

set -e

echo "🚀 Deploying StaffProBot..."

# Переход в директорию проекта
cd /opt/staffprobot

# Обновление кода
git pull origin main

# Сборка и запуск
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Ожидание готовности сервисов
sleep 30

# Проверка здоровья
./scripts/health-check.sh

echo "✅ Deployment completed!"
