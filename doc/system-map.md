# System map

StaffProBot Platform (staffprobot.ru)

```
Roles (Owner / Manager / Employee / Applicant / Superadmin)
│
├── Web (FastAPI) — /owner/*, /manager/*, /employee/*, /admin/*, /moderator/*
│   Jinja2, Bootstrap 5, FullCalendar, HTMX, vanilla JS
└── Bots
    ├── Telegram Bot (python-telegram-bot) — webhook, PIN for web login
    └── MAX Bot (platform-api.max.ru) — webhook, same business logic via adapters
        │
        ▼
Core (apps/web, apps/bot, shared/, domain/)
        │
        ├── Objects, TimeSlots, Shifts, Contracts, Templates
        ├── PayrollEntry, Adjustments, Billing, Tariffs
        ├── Reviews, Ratings, Notifications (web + Telegram, auto-login links)
        ├── Offers, Applications, Documents (MinIO/S3)
        └── NotificationDispatcher, NotificationActionService
        │
        ▼
PostgreSQL (PostGIS) + Redis + RabbitMQ
        │
        ├── Celery (celery_worker, celery_beat) — payroll, reminders, scheduled tasks
        ├── YooKassa — payments
        ├── WeasyPrint / ReportLab — PDF contracts
        └── Telegram Bot API
        │
        ▼
Deploy: Docker Compose (prod), GitHub Actions → SSH pull, health check, deployments table
```
