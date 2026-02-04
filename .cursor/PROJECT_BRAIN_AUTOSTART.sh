#!/bin/bash
# Скрипт для установки и настройки автозапуска Project Brain

set -e

PROJECT_DIR="/home/sa/projects/project-brain"
SERVICE_FILE="/etc/systemd/system/project-brain.service"

echo "🔍 Проверка Project Brain..."

# Проверка существования директории
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Директория $PROJECT_DIR не найдена!"
    echo "📝 Создайте проект или укажите правильный путь"
    exit 1
fi

# Проверка docker-compose файла
if [ ! -f "$PROJECT_DIR/docker-compose.local.yml" ]; then
    echo "❌ Файл docker-compose.local.yml не найден!"
    exit 1
fi

echo "✅ Проект найден: $PROJECT_DIR"

# Запуск контейнеров
echo "🚀 Запуск контейнеров..."
cd "$PROJECT_DIR"
docker compose -f docker-compose.local.yml up -d

echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка здоровья
echo "🔍 Проверка здоровья API..."
if curl -s http://192.168.2.107:8003/health > /dev/null 2>&1; then
    echo "✅ Project Brain запущен и работает!"
else
    echo "⚠️  API ещё не готов, проверьте логи:"
    echo "   docker compose -f $PROJECT_DIR/docker-compose.local.yml logs"
fi

# Создание systemd сервиса
echo "📝 Создание systemd сервиса..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Project Brain Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker compose -f docker-compose.local.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.local.yml down
TimeoutStartSec=0
User=sa
Group=sa

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
sudo systemctl daemon-reload

# Включение автозапуска
echo "🔧 Включение автозапуска..."
sudo systemctl enable project-brain.service

# Запуск сервиса
echo "▶️  Запуск сервиса..."
sudo systemctl start project-brain.service

# Проверка статуса
echo "📊 Статус сервиса:"
sudo systemctl status project-brain.service --no-pager

echo ""
echo "✅ Готово! Project Brain настроен на автозапуск."
echo "📝 Для проверки после перезагрузки:"
echo "   sudo systemctl status project-brain.service"
echo "   curl http://192.168.2.107:8003/health"
