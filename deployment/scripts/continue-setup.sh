#!/bin/bash
# Скрипт продолжения установки с места остановки

set -e

DOMAIN="staffprobot.ru"
USER="staffprobot"
PROJECT_DIR="/opt/sites/staffprobot"

echo "🔄 Продолжение установки StaffProBot с места остановки"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo $0"
    exit 1
fi

# Проверка существования swap файла
echo "💾 Проверка swap файла..."
if [ -f /swapfile ]; then
    echo "Swap файл существует, проверяем статус..."
    if ! swapon --show | grep -q /swapfile; then
        echo "Активируем существующий swap файл..."
        swapon /swapfile
        echo "✅ Swap файл активирован"
    else
        echo "✅ Swap файл уже активен"
    fi
else
    echo "❌ Swap файл не найден. Запустите полную установку: setup-server.sh"
    exit 1
fi

# Проверка пользователя
echo "👤 Проверка пользователя $USER..."
if ! id "$USER" &>/dev/null; then
    echo "❌ Пользователь $USER не найден. Запустите полную установку: setup-server.sh"
    exit 1
fi

# Проверка директории проекта
echo "📁 Проверка директории проекта..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Директория $PROJECT_DIR не найдена. Запустите полную установку: setup-server.sh"
    exit 1
fi

# Продолжение с настройки логирования
echo "📝 Настройка логирования..."
mkdir -p /var/log/staffprobot
chown $USER:$USER /var/log/staffprobot

# Создание systemd сервиса для мониторинга
echo "🔍 Создание сервиса мониторинга..."
cat > /etc/systemd/system/staffprobot-monitor.service << EOF
[Unit]
Description=StaffProBot Monitoring
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable staffprobot-monitor

# Создание скрипта деплоя
echo "🚀 Создание скрипта деплоя..."
cat > $PROJECT_DIR/deploy.sh << 'EOF'
#!/bin/bash
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
EOF

chmod +x $PROJECT_DIR/deploy.sh
chown $USER:$USER $PROJECT_DIR/deploy.sh

# Создание скрипта проверки здоровья
echo "🏥 Создание скрипта проверки здоровья..."
cat > $PROJECT_DIR/scripts/health-check.sh << 'EOF'
#!/bin/bash

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
EOF

chmod +x $PROJECT_DIR/scripts/health-check.sh
chown $USER:$USER $PROJECT_DIR/scripts/health-check.sh

# Создание директории для логов
mkdir -p $PROJECT_DIR/logs
chown $USER:$USER $PROJECT_DIR/logs

# Настройка ротации логов
echo "📋 Настройка ротации логов..."
cat > /etc/logrotate.d/staffprobot << EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload nginx
    endscript
}
EOF

echo "✅ Продолжение установки завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Скопируйте SSH ключ для пользователя $USER"
echo "2. Запустите: sudo -u $USER git clone <repository> $PROJECT_DIR"
echo "3. Настройте DNS записи для $DOMAIN"
echo "4. Запустите: sudo ./deployment/scripts/setup-ssl.sh"
echo "5. Запустите: sudo -u $USER $PROJECT_DIR/deploy.sh"
echo ""
echo "🌐 После настройки сайт будет доступен по адресу: https://$DOMAIN"
