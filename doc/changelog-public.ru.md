# Публичный changelog (маркетинговый)

## 2026-03 — Подготовка к MAX-боту

- **Модель данных:** при регистрации создаётся запись в `messenger_accounts`; report chat читается из `notification_targets` (fallback на legacy поля)
- **Веб:** исправлено разделение user_id и telegram_id в owner-интерфейсе; при редактировании объекта записывается target для Telegram
- **Celery/бот:** все места получения report chat переведены на единый сервис notification_targets
