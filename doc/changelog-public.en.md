# Public Changelog (marketing)

## 2026-03 — MAX bot preparation

- **Data model:** `messenger_accounts` on registration; report chat from `notification_targets` (legacy fallback)
- **Web:** fixed user_id vs telegram_id separation in owner UI; object edit persists telegram target
- **Celery/bot:** report chat resolution unified via notification_target_service
