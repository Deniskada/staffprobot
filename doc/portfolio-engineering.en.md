# StaffProBot — Portfolio Engineering (EN)

**MAX bot: full implementation cycle (2026-03):** Added a second messenger (MAX) without duplicating business logic. Architecture: `NormalizedUpdate` DTO → `TgAdapter`/`MaxAdapter` parsers → `UnifiedBotRouter` dispatch → shared handlers → `TgMessenger`/`MaxMessenger` output. ~3500 lines of new unified handlers (shifts, objects, scheduling, tasks, messenger linking). `MaxClient` for text/photo/callback. Account linking via one-time codes. Dual-channel notifications (`NotificationDispatcher` + `MaxNotificationSender`). `notification_targets` for TG+MAX group chats at object and org-unit level. Production deploy: nginx, DNS/TLS, webhook, feature flag with rollback. CI: 28 smoke tests gate. 106 files, +7400 / −1500 lines.

**Phase 1 MAX (2026-03):** messenger_accounts on registration, notification_targets read/write, user_id/telegram_id separation in owner.py, unified get_telegram_report_chat_id_for_object in bot and Celery.
