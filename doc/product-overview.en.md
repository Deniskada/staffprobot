# StaffProBot Platform

## Product Summary

StaffProBot is a platform for managing shifts, staff and payouts. Owners and managers maintain objects (locations) and schedules; employees work shifts; the system calculates pay, sends notifications and supports contracts and document templates. Access is via bots in Telegram and MAX or a web app (FastAPI); roles include owner, manager, employee, applicant and superadmin. The platform covers geolocation (PostGIS), calendar planning with time slots, contract templates and versions, payroll with adjustments and billing, reviews and ratings, and notifications with one-click login links to the web app.

## Business Problem

Companies that run multiple locations and shift-based staff face manual scheduling, contract handling, pay calculation errors and poor visibility for employees. Coordinating shifts, contracts and pay across owners, managers and staff without a single system leads to double entry, disputes and delayed payments.

## Solution

StaffProBot provides one backend for the Telegram bot and the web app. Objects have addresses and schedules; time slots define when shifts are needed; shifts assign employees. The web calendar supports drag-and-drop planning; the bot supports planning, reports and PIN-based web login. Contracts use templates and versions; a constructor (master) is in progress. Payroll is calculated from shifts with contract/slot/object rate priority; adjustments and payout schedules are supported. Notifications (shift, contract, offer, reminders) are sent to Telegram and web, each with an auto-login link to the relevant page. Reviews and ratings with moderation and appeals are implemented. CI/CD runs tests and deploys to production via GitHub Actions.

## Key Capabilities

- **Roles and access:** Owner, manager, employee, applicant, superadmin; multiple roles per user; routing by prefix in `app.py` (/owner, /manager, /employee); JWT and Telegram auth; PIN from bot for web login.
- **Objects and shifts:** Objects with address and schedule; time slots (with max_employees); shifts; calendar (FullCalendar) with drag-and-drop; PostGIS for geolocation and “available for applicants”; filters and map.
- **Contracts and documents:** Templates, versions, constructor (in progress); contract conclusion and history; PDF generation (WeasyPrint).
- **Payroll and billing:** PayrollEntry, adjustments, rate priority (contract → slot → object); payout schedules; billing, tariffs, limits; YooKassa integration.
- **Reviews and ratings:** Reviews for employees and objects; moderation; appeals; reports.
- **Notifications:** Telegram, MAX and web; types (shift, contract, offer, reminders, etc.); auto-login URL in every message (NotificationActionService.get_action_url); owners configure delivery channels.
- **Bots (Telegram + MAX):** Unified business logic via `UnifiedBotRouter` — shifts, objects, scheduling, tasks, reports, geolocation; `TgAdapter`/`MaxAdapter` normalize incoming updates, `TgMessenger`/`MaxMessenger` handle outgoing; account linking via one-time codes in the dashboard.
- **Multi-messenger architecture:** `NormalizedUpdate` DTO, `messenger_accounts` (one user — multiple messengers), `notification_targets` (TG+MAX group chats at object/org level), `MAX_FEATURES_ENABLED` feature flag with rollback.
- **DevOps:** Docker Compose (dev/prod), health checks, GitHub Actions (test, lint, security, deploy to 155.212.217.38), deployments table.

## Architecture Overview

The system map (`doc/system-map.md`) describes the flow: **Roles** (owner, manager, employee, applicant, superadmin) use **Web** (FastAPI, Jinja2, Bootstrap 5, FullCalendar) or **Telegram Bot**. The **Core** (apps/web, apps/bot, shared/, domain/) uses **PostgreSQL (PostGIS)**, **Redis** and **RabbitMQ**. **Celery** runs payroll and scheduled tasks. **YooKassa** handles payments; **WeasyPrint/ReportLab** generate PDFs. Deploy is Docker Compose on production with Nginx and Let's Encrypt; CI/CD via GitHub Actions.

## Integrations

| System | Role |
|--------|------|
| **PostgreSQL + PostGIS** | Main DB; geodata for objects and location checks |
| **Redis** | Cache, sessions |
| **RabbitMQ** | Message queue for Celery |
| **Celery** | Payroll jobs, reminders, scheduled tasks |
| **YooKassa** | Payments, billing |
| **Telegram Bot API** | Bot webhook, messages, PIN for web login |
| **MAX platform-api.max.ru** | MAX bot webhook, messages, account linking |
| **MinIO/S3** | Document and media storage (optional messenger storage) |
| **WeasyPrint / ReportLab** | PDF contracts |

## Business Impact

- **Single system:** One place for objects, shifts, contracts and pay; less double entry and fewer errors.
- **Clear roles:** Owners, managers and employees have dedicated interfaces and permissions.
- **Transparent pay:** Rate priority and adjustments are defined; payout schedules and billing are supported.
- **Faster actions:** Notifications with direct links to the web app; bot for quick planning and reports.
- **Scalable foundation:** Four product modules in roadmap (shift marketplace, smart planning, auto pay, EDO); current codebase is the base for all.
