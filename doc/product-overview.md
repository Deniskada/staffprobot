# StaffProBot Platform

## Product Summary

StaffProBot is a platform for managing shifts, staff and payouts. Owners and managers maintain objects (locations) and schedules; employees work shifts; the system calculates pay, sends notifications and supports contracts and document templates. Access is via a Telegram bot or a web app (FastAPI); roles include owner, manager, employee, applicant and superadmin. The platform covers geolocation (PostGIS), calendar planning with time slots, contract templates and versions, payroll with adjustments and billing, reviews and ratings, and notifications with one-click login links to the web app.

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
- **Notifications:** Telegram and web; types (shift, contract, offer, reminders, etc.); auto-login URL in every Telegram message (NotificationActionService.get_action_url).
- **Telegram bot:** Planning, reports (including Excel), object selection by location, PIN for web, view shifts and offers.
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
| **MinIO/S3** | Document and media storage (optional Telegram storage) |
| **WeasyPrint / ReportLab** | PDF contracts |

## Business Impact

- **Single system:** One place for objects, shifts, contracts and pay; less double entry and fewer errors.
- **Clear roles:** Owners, managers and employees have dedicated interfaces and permissions.
- **Transparent pay:** Rate priority and adjustments are defined; payout schedules and billing are supported.
- **Faster actions:** Notifications with direct links to the web app; bot for quick planning and reports.
- **Scalable foundation:** Four product modules in roadmap (shift marketplace, smart planning, auto pay, EDO); current codebase is the base for all.

---

# Платформа StaffProBot (рус.)

## Краткое описание продукта

StaffProBot — платформа для управления сменами, персоналом и выплатами. Владельцы и управляющие ведут объекты и расписания; сотрудники работают по сменам; система считает зарплату, отправляет уведомления и поддерживает договоры и шаблоны документов. Доступ — через Telegram-бот или веб-приложение (FastAPI); роли: владелец, управляющий, сотрудник, соискатель, суперадмин. Реализованы геолокация (PostGIS), календарное планирование с тайм-слотами, шаблоны и версии договоров, расчёт зарплаты с корректировками и биллингом, отзывы и рейтинги, уведомления со ссылками авто-логина в веб.

## Бизнес-проблема

Компании с несколькими точками и сменным персоналом сталкиваются с ручным планированием, оформлением договоров, ошибками в расчёте зарплаты и плохой информированностью сотрудников. Координация смен, договоров и выплат без единой системы ведёт к двойному вводу, спорам и задержкам выплат.

## Решение

StaffProBot даёт один бэкенд для Telegram-бота и веб-приложения. Объекты имеют адреса и графики; тайм-слоты задают потребность в сменах; смены назначают сотрудников. Веб-календарь поддерживает планирование drag-and-drop; бот — планирование, отчёты и выдачу PIN для входа в веб. Договоры строятся на шаблонах и версиях; конструктор (мастер) в разработке. Зарплата считается по сменам с приоритетом ставок (договор → слот → объект); поддерживаются корректировки и графики выплат. Уведомления (смена, договор, оффер, напоминания) отправляются в Telegram и веб, в каждое сообщение подставляется ссылка с авто-логином. Реализованы отзывы и рейтинги с модерацией и обжалованиями. CI/CD прогоняет тесты и деплоит на прод через GitHub Actions.

## Ключевые возможности

- **Роли и доступ:** владелец, управляющий, сотрудник, соискатель, суперадмин; несколько ролей у пользователя; роутинг по префиксу в app.py (/owner, /manager, /employee); JWT и авторизация через Telegram; PIN из бота для входа в веб.
- **Объекты и смены:** объекты с адресом и графиком; тайм-слоты (в т.ч. max_employees); смены; календарь (FullCalendar) с drag-and-drop; PostGIS для геолокации и «доступен для соискателей»; фильтры и карта.
- **Договоры и документы:** шаблоны, версии, конструктор (в разработке); заключение договоров и история; генерация PDF (WeasyPrint).
- **Расчёт и биллинг:** PayrollEntry, корректировки, приоритет ставок (договор → слот → объект); графики выплат; биллинг, тарифы, лимиты; интеграция с YooKassa.
- **Отзывы и рейтинги:** отзывы по сотрудникам и объектам; модерация; обжалования; отчёты.
- **Уведомления:** Telegram и веб; типы (смена, договор, оффер, напоминания и др.); в каждое Telegram-сообщение подставляется URL с авто-логином (NotificationActionService.get_action_url).
- **Telegram-бот:** планирование, отчёты (в т.ч. Excel), выбор объектов по местоположению, выдача PIN для веб-входа, просмотр смен и офферов.
- **DevOps:** Docker Compose (dev/prod), health checks, GitHub Actions (тесты, линт, безопасность, деплой на 155.212.217.38), таблица deployments.

## Обзор архитектуры

Карта системы (`doc/system-map.md`) описывает поток: **Роли** (владелец, управляющий, сотрудник, соискатель, суперадмин) используют **Веб** (FastAPI, Jinja2, Bootstrap 5, FullCalendar) или **Telegram-бот**. **Ядро** (apps/web, apps/bot, shared/, domain/) использует **PostgreSQL (PostGIS)**, **Redis** и **RabbitMQ**. **Celery** выполняет задачи по расчёту и расписанию. **YooKassa** — платежи; **WeasyPrint/ReportLab** — PDF договоров. Деплой — Docker Compose на проде с Nginx и Let's Encrypt; CI/CD через GitHub Actions.

## Интеграции

| Система | Назначение |
|--------|------------|
| **PostgreSQL + PostGIS** | Основная БД; геоданные объектов и проверка местоположения |
| **Redis** | Кэш, сессии |
| **RabbitMQ** | Очередь для Celery |
| **Celery** | Расчёт зарплаты, напоминания, отложенные задачи |
| **YooKassa** | Платежи, биллинг |
| **Telegram Bot API** | Webhook бота, сообщения, PIN для веб-входа |
| **MinIO/S3** | Хранение документов и медиа (опционально Telegram) |
| **WeasyPrint / ReportLab** | PDF договоров |

## Влияние на бизнес

- **Единая система:** один контур для объектов, смен, договоров и выплат; меньше двойного ввода и ошибок.
- **Понятные роли:** у владельцев, управляющих и сотрудников свои интерфейсы и права.
- **Прозрачная зарплата:** заданы приоритет ставок и корректировки; поддержаны графики выплат и биллинг.
- **Быстрые действия:** уведомления со прямыми ссылками в веб; бот для планирования и отчётов.
- **Масштабируемый фундамент:** в дорожной карте четыре модуля (биржа смен, умное планирование, авто-выплаты, ЭДО); текущая кодовая база — основа для всех.
