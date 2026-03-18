# StaffProBot — описание проекта

## Технологии

| Слой | Стек |
|------|------|
| **Язык** | Python 3.11+ |
| **Веб** | FastAPI, Uvicorn, Jinja2, JWT (python-jose, PyJWT), passlib/bcrypt |
| **БД** | PostgreSQL 15 + PostGIS, SQLAlchemy 1.4, asyncpg, Alembic |
| **Кэш/очереди** | Redis, RabbitMQ, Celery |
| **Бот** | python-telegram-bot 20.x |
| **Фронт** | Bootstrap 5, FullCalendar.js, Chart.js, HTMX, vanilla JS |
| **Медиа** | MinIO/S3 (boto3), опционально хранение в Telegram |
| **Платежи** | YooKassa |
| **PDF** | WeasyPrint, ReportLab |
| **Прочее** | Pydantic, geopy, shapely, pandas, openpyxl, httpx, Yandex GPT (openai-совместимый), Prometheus |

## Размер

- **Файлы:** ~860+ (Python, HTML, JS, YAML; без .git).
- **Строки кода:** ~146 000 (Python), ~240 000 с шаблонами и статикой.
- **Структура:** монорепозиторий — `apps/web`, `apps/bot`, `apps/scheduler`, `apps/api`, `apps/analytics`; `core/`, `shared/`, `domain/`; миграции Alembic в `migrations/`.

## Функции (что делает проект)

Платформа для управления сменами, персоналом и выплатами: владелец/управляющий ведёт объекты и графики, сотрудники работают по сменам, система считает зарплату и отправляет уведомления.

- **Роли:** владелец (owner), управляющий (manager), сотрудник (employee), соискатель. Один пользователь может иметь несколько ролей. Вход: Telegram-бот или логин/пароль в веб (PIN из бота для привязки).
- **Объекты и смены:** точки (объекты) с адресом и графиком работы; тайм-слоты по дням/времени; смены — назначение сотрудника на слот. Календарь с drag&drop планированием (веб), синхрон с ботом. Геолокация (PostGIS), фильтр «доступен для соискателей».
- **Договоры и ЭДО:** шаблоны договоров, версии, конструктор (мастер создания шаблонов). Заключение договоров с сотрудниками, привязка к объектам. История изменений договора (Contract History). Генерация PDF (WeasyPrint).
- **Сотрудники и найм:** профили сотрудников, документы профиля (загрузка, отклонение). Офферы (предложения смен) — сотрудник/соискатель принимает или отклоняет. Адресная книга (контакты).
- **Расчёт и выплаты:** начисления по сменам (повременная, окладная, повременно-премиальная). Приоритет ставок: договор → тайм-слот → объект. Задачи на смену (обязательные/необязательные), штрафы и премии (Celery). Корректировки (adjustments), графики выплат (ежедневно/еженедельно/ежемесячно). Биллинг, тарифы, лимиты, подписки. Интеграция с YooKassa.
- **Отзывы и рейтинги:** отзывы по сотрудникам и объектам, рейтинги, модерация, обжалования. Отчёты по отзывам.
- **Уведомления:** Telegram и веб; типы — смена, договор, оффер, напоминания, дни рождения, праздники и др. В каждое сообщение подставляется ссылка с авто-логином в ЛК.
- **Telegram-бот:** планирование смен, отчёты (в т.ч. Excel), выбор объектов по геолокации, выдача PIN для входа в веб, просмотр своих смен и офферов.
- **Дополнительно:** инциденты, задачи (owner/manager/employee), продукты объекта, правила, причины отмен. Медиа (MinIO/S3 или Telegram), прокси медиа и геокодинга. Админ: пользователи, системные настройки, отчёты, таблица деплоев.

## Workflow (полный цикл)

### Разработка

1. **Запуск:** `docker compose -f docker-compose.dev.yml up -d`
2. **Сервисы:** postgres (PostGIS, порт 5433), redis (6379), rabbitmq (5672, UI 15672), minio (9000/9001), **web** (uvicorn :8001), **bot** (main.py, :8000), **celery_worker**, **celery_beat**
3. **Перезапуск после правок:**  
   - только web → `restart web`; только bot → `restart bot`;  
   - правки в `shared/` или `domain/` → `restart web bot celery_worker celery_beat`
4. **Команды внутри контейнеров:** `docker compose -f docker-compose.dev.yml exec web ...` / `... exec bot ...`

### Роли и приложение

- **Роутинг по ролям:** префиксы задаются в `apps/web/app.py` (`/owner`, `/manager`, `/employee`). В роутах дублировать префиксы нельзя.
- **Вход:** Telegram (бот) или логин/пароль (веб). Связка пользователя с БД — внутренний `user_id`, не `telegram_id`.
- **Уведомления:** Telegram-сообщения с авто-логином по ссылке в ЛК; шаблоны в `shared/templates/notifications/base_templates.py`, маппинг тип→URL в `NotificationActionService.get_action_url()`.

### CI/CD (GitHub Actions)

1. **Триггер:** push / PR в `main`
2. **Джобы:**  
   - **test:** pytest (PostgreSQL + Redis в services), coverage → Codecov  
   - **lint:** black, flake8, mypy  
   - **security:** safety (requirements.txt), bandit  
3. **deploy:** при push в `main` и успехе test/lint/security — SSH на прод, `git pull`, `docker compose -f docker-compose.prod.yml up -d`, проверка health, запись в таблицу `deployments`
4. **notify:** опционально уведомление в Telegram о результате сборки

### Деплой (production)

- Сервер: по текущему workflow — `root@155.212.217.38`, путь `/opt/sites/staffprobot`
- Продакшен: `docker-compose.prod.yml`, те же сервисы (postgres, redis, rabbitmq, web, bot, celery_worker, celery_beat) без volume-mount кода

### Документация и планы

- **Roadmap:** `doc/plans/roadmap.md` (фазы, эпики, модули: биржа смен, планирование, расчёт/выплаты, ЭДО)
- **Цели:** `doc/plans/goals_map.md`, `doc/plans/goals_optimization.md`
- **Видение/технологии (расширенно):** `doc/vision.md`
- **Правила кода:** `.cursor/rules/staffprobot.mdc` (user_id vs telegram_id, URLHelper, статика, уведомления с авто-логином)
