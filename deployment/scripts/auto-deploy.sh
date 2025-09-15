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

log "6) Поднятие сервисов docker-compose.prod.yml"
export IMAGE_NAME=staffprobot IMAGE_TAG=latest
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

log "7) Проверка здоровья"
sleep 10
su -s /bin/bash -c "$PROJECT_DIR/scripts/health-check.sh" staffprobot || fail "Health-check не пройден"

log "✅ Готово. Приложение запущено."
