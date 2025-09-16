#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."  # в корень репозитория

echo "[bootstrap] Старт первичной настройки прод-среды"

ENV_FILE=".env.prod"

if [ ! -f "$ENV_FILE" ]; then
  echo "[bootstrap] Создаю $ENV_FILE"
  POSTGRES_PASSWORD_GEN=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)
  REDIS_PASSWORD_GEN=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)
  SECRET_KEY_GEN=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 48)

  cat > "$ENV_FILE" <<EOF
ENVIRONMENT=production
DEBUG=false

# Postgres
POSTGRES_DB=staffprobot_prod
POSTGRES_USER=staffpro
POSTGRES_PASSWORD=${POSTGRES_PASSWORD_GEN}

# Redis
REDIS_PASSWORD=${REDIS_PASSWORD_GEN}

# RabbitMQ
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# App
SECRET_KEY=${SECRET_KEY_GEN}
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
EOF
  echo "[bootstrap] Файл $ENV_FILE создан. Впишите TELEGRAM_BOT_TOKEN и при необходимости OPENAI_API_KEY."
fi

if ! grep -q "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" || [ -z "$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)" ]; then
  echo -n "[bootstrap] Введите TELEGRAM_BOT_TOKEN: "
  read -r TBTK || true
  if [ -n "${TBTK:-}" ]; then
    sed -i -E "s|^TELEGRAM_BOT_TOKEN=.*$|TELEGRAM_BOT_TOKEN=${TBTK}|" "$ENV_FILE"
  fi
fi

echo "[bootstrap] Поднимаю Postgres/Redis/RabbitMQ"
docker-compose -f docker-compose.prod.yml up -d postgres redis rabbitmq

echo "[bootstrap] Прогоняю Alembic миграции (migrator)"
docker-compose -f docker-compose.prod.yml run --rm migrator

echo "[bootstrap] Запускаю приложения (web/bot/celery) с override"
docker-compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d web bot celery_worker celery_beat

echo "[bootstrap] Настраиваю systemd unit+timer для автодеплоя"
sudo cp -f deployment/systemd/staffprobot-deploy.service /etc/systemd/system/staffprobot-deploy.service
sudo cp -f deployment/systemd/staffprobot-deploy.timer /etc/systemd/system/staffprobot-deploy.timer
sudo systemctl daemon-reload
sudo systemctl enable --now staffprobot-deploy.timer

echo "[bootstrap] Готово. Проверка health:"
curl -sS http://127.0.0.1:8000/health || true

echo "[bootstrap] Автодеплой включён (systemd timer). Скрипт деплоя: deployment/scripts/auto-deploy.sh"

