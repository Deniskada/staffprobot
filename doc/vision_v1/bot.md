# Telegram бот StaffProBot

## Архитектура

- `apps/bot/bot.py` — основной модуль с `StaffProBot`.
- Token конфигурация:
  - `TELEGRAM_BOT_TOKEN_PROD` — используется только при `ENVIRONMENT=production`
  - `TELEGRAM_BOT_TOKEN_DEV` — по умолчанию в dev и локальных docker‑контейнерах
  - `TELEGRAM_BOT_TOKEN_OVERRIDE` — ручной override (priority > prod/dev)
- Настройки читаются через `core/config/settings.py`. Legacy `TELEGRAM_BOT_TOKEN` поддерживается для обратной совместимости, но не используется в новых окружениях.

## Polling lock и heartbeat

- Redis ключ `bot_polling_lock`:
  ```json
  {"host": "...", "pid": 1234, "env": "production", "ts": "2025-11-19T06:15:00.123456+00:00"}
  ```
  гарантирует единственный polling‑процесс. При запуске dev‑бота lock проверяется, иначе процесс завершается.
- Heartbeat (`bot_polling_heartbeat`) обновляется каждые 20 сек. `bot_polling_heartbeat_timestamp` (Prometheus gauge) хранит UNIX timestamp последнего обновления.
- CLI для форс‑снятия lock: `python scripts/release_bot_lock.py`.

## Мониторинг и алерты

- Метрики (`core/monitoring/metrics.py`):
  - `staffprobot_bot_polling_conflicts_total` — количество `telegram.error.Conflict`
  - `staffprobot_bot_polling_heartbeat_timestamp` — timestamp heartbeat
- Celery задача `monitor_bot_heartbeat`:
  - запускается каждую минуту;
  - если heartbeat отсутствует >5 минут, создаёт уведомление (IN_APP + Telegram, `NotificationType.SYSTEM_MAINTENANCE`) всем суперадминам, записывает лог и устанавливает флаг `bot_polling_alert_sent` в Redis;
  - при восстановлении heartbeat флаг очищается.

## Runbook «бот не отвечает»

1. `docker compose -f docker-compose.prod.yml logs bot --tail 200`
2. Проверить lock/heartbeat:
   ```bash
   docker compose -f docker-compose.prod.yml exec redis redis-cli get bot_polling_lock
   docker compose -f docker-compose.prod.yml exec redis redis-cli get bot_polling_heartbeat
   ```
3. Если lock «завис» — `python scripts/release_bot_lock.py`
4. Очистить очередь: `curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN_PROD/getUpdates?offset=-1&drop_pending_updates=true"`
5. Перезапустить контейнер `bot`
6. Убедиться, что heartbeat появился и метрика обновилась.

## Dev checklist

- В `.env`/`.env.dev` должен быть заполнен `TELEGRAM_BOT_TOKEN_DEV`; prod токен запрещён.
- Перед запуском dev‑бота убедиться, что lock свободен.
- После остановки dev‑бота всегда выполняйте `drop_pending_updates=true`, чтобы не блокировать прод.

