# Public Changelog (marketing)

## 2026-03 — MAX bot launched in production

- **Second messenger:** StaffProBot now works in both Telegram and MAX — single business logic, two delivery channels
- **Shifts and objects:** opening/closing shifts, object management, scheduling, tasks — all available through both messengers
- **Account linking:** users connect MAX to their StaffProBot account via a one-time code in the dashboard
- **Notifications:** personal and group notifications reach Telegram and/or MAX based on owner settings
- **Report chats:** owners configure Telegram and MAX chats for objects and organizations
- **Web UI:** employee cards, contracts, manager forms updated for both messengers

## 2026-03 — MAX bot preparation (Phase 1)

- **Data model:** `messenger_accounts` on registration; report chat from `notification_targets` (legacy fallback)
- **Web:** fixed user_id vs telegram_id separation in owner UI; object edit persists telegram target
- **Celery/bot:** report chat resolution unified via notification_target_service
