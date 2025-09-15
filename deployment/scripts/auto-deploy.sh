#!/bin/bash
# Автоматизированный деплой StaffProBot (все-в-одном)
# Использование: sudo ./deployment/scripts/auto-deploy.sh

set -euo pipefail

DOMAIN=${DOMAIN:-staffprobot.ru}
PROJECT_DIR=/opt/staffprobot
ENV_FILE=$PROJECT_DIR/.env.prod
DOCKERFILE=$PROJECT_DIR/docker/Dockerfile

log() { echo -e "[$(date +'%F %T')] $*"; }
fail() { echo -e "❌ $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "Запустите с sudo/от root"

log "1) Проверка директории проекта"
[ -d "$PROJECT_DIR" ] || fail "Нет $PROJECT_DIR. Клонируйте репозиторий туда."
chown -R staffprobot:staffprobot "$PROJECT_DIR" || true

log "2) Проверка .env.prod"
if [ ! -f "$ENV_FILE" ]; then
  fail "Не найден $ENV_FILE. Создайте из deployment/env.prod.example и заполните."
fi
# Базовая валидация ключевых переменных
source "$ENV_FILE"
for v in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD REDIS_PASSWORD RABBITMQ_USER RABBITMQ_PASSWORD SECRET_KEY TELEGRAM_BOT_TOKEN GRAFANA_PASSWORD; do
  [ -n "${!v:-}" ] || fail "Переменная $v пуста в .env.prod"
done

log "3) Проверка SSL сертификатов"
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  log "Сертификаты не найдены, запускаю setup-ssl.sh"
  bash $PROJECT_DIR/deployment/scripts/setup-ssl.sh
fi

log "4) Патчим Dockerfile (bookworm + https зеркала)"
sed -i 's|^FROM python:3\.11-slim.*|FROM python:3.11-slim-bookworm as base|' "$DOCKERFILE" || true
if ! grep -q "deb.debian.org" "$DOCKERFILE"; then
  # уже пропатчен ранее нашим коммитом — пропускаем
  true
fi

log "5) Сборка локального образа с сетью host"
cd "$PROJECT_DIR"
su -s /bin/bash -c "docker build --network=host -t staffprobot:latest -f docker/Dockerfile ." staffprobot

log "6) Подготовка конфигов мониторинга (Prometheus/Grafana)"
# Гарантируем наличие директории и файла Prometheus на хосте
mkdir -p "$PROJECT_DIR/deployment/monitoring"
if [ ! -f "$PROJECT_DIR/deployment/monitoring/prometheus.yml" ]; then
  curl -fsSL -o "$PROJECT_DIR/deployment/monitoring/prometheus.yml" \
    "https://raw.githubusercontent.com/Deniskada/staffprobot/main/deployment/monitoring/prometheus.yml" || \
    fail "Не удалось скачать prometheus.yml"
fi

# Обновим маунт Prometheus на директорию, чтобы избежать ошибок file/dir
if grep -q "deployment/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml" "$PROJECT_DIR/docker-compose.prod.yml"; then
  sed -i "s#\./deployment/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro#\./deployment/monitoring:/etc/prometheus:ro#" "$PROJECT_DIR/docker-compose.prod.yml"
fi

log "7) Поднятие сервисов docker-compose.prod.yml"
export IMAGE_NAME=staffprobot IMAGE_TAG=latest
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

log "8) Проверка здоровья"
sleep 10
su -s /bin/bash -c "$PROJECT_DIR/scripts/health-check.sh" staffprobot || fail "Health-check не пройден"

log "✅ Готово. Приложение запущено."
