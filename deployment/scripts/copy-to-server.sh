#!/bin/bash
# Скрипт для копирования проекта на сервер

set -e

SERVER_IP=$1
SERVER_USER="staffprobot"
PROJECT_DIR="/opt/staffprobot"

if [ -z "$SERVER_IP" ]; then
    echo "❌ Использование: $0 <SERVER_IP>"
    echo "Пример: $0 192.168.1.100"
    exit 1
fi

echo "🚀 Копирование проекта на сервер $SERVER_IP"

# Проверка подключения к серверу
echo "🔍 Проверка подключения к серверу..."
if ! ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER_IP "echo 'Подключение успешно'"; then
    echo "❌ Не удается подключиться к серверу $SERVER_IP"
    echo "Убедитесь, что:"
    echo "1. Сервер запущен и доступен"
    echo "2. SSH ключ настроен для пользователя $SERVER_USER"
    echo "3. Пользователь $SERVER_USER существует на сервере"
    exit 1
fi

# Создание архива проекта
echo "📦 Создание архива проекта..."
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env*' \
    --exclude='node_modules' \
    --exclude='.pytest_cache' \
    --exclude='coverage' \
    --exclude='.coverage' \
    -czf staffprobot.tar.gz .

# Копирование архива на сервер
echo "📤 Копирование архива на сервер..."
scp staffprobot.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

# Распаковка на сервере
echo "📥 Распаковка на сервере..."
ssh $SERVER_USER@$SERVER_IP "
    cd $PROJECT_DIR
    sudo rm -rf *
    sudo tar -xzf /tmp/staffprobot.tar.gz -C $PROJECT_DIR
    sudo chown -R $SERVER_USER:$SERVER_USER $PROJECT_DIR
    rm /tmp/staffprobot.tar.gz
"

# Очистка локального архива
rm staffprobot.tar.gz

echo "✅ Проект успешно скопирован на сервер!"
echo ""
echo "📋 Следующие шаги на сервере:"
echo "1. Настройте переменные окружения:"
echo "   sudo -u $SERVER_USER cp $PROJECT_DIR/deployment/env.prod.example $PROJECT_DIR/.env.prod"
echo "   sudo -u $SERVER_USER nano $PROJECT_DIR/.env.prod"
echo ""
echo "2. Настройте SSL сертификаты:"
echo "   sudo $PROJECT_DIR/deployment/scripts/setup-ssl.sh"
echo ""
echo "3. Запустите приложение:"
echo "   sudo -u $SERVER_USER $PROJECT_DIR/deploy.sh"
