# DevOps Command Center - MVP

## 🎯 Обзор

DevOps Command Center — это централизованная система для мониторинга, поддержки пользователей и автоматизации разработки проекта StaffProBot.

**Статус:** MVP реализован ✅

## 📊 Компоненты

### 1. Support Hub (Веб-интерфейс)

**Доступ:** `/support` (для всех ролей)

**Функции:**
- **Hub** (`/support`) - главная страница с количеством багов пользователя
- **Bug Report** (`/support/bug`) - форма подачи бага с приоритетом
- **FAQ** (`/support/faq`) - база знаний с категориями
- **My Bugs** (`/support/my-bugs`) - список моих багов со статусами

**База данных:**
- `bug_logs` - отчеты о багах с приоритетами и статусами
- `faq_entries` - вопросы и ответы по категориям

### 2. Admin DevOps Dashboard

**Доступ:** `/admin/devops` (owner, superadmin)

**Метрики:**
- **DORA Metrics:**
  - Deployment Frequency - частота деплоев за 30 дней
  - Change Failure Rate - процент провалов деплоев
- **Статистика деплоев:** общее количество, успешные, провалы
- **GitHub Issues:** количество багов, критичных задач
- **Системный статус:** Web, Bot, DB онлайн/офлайн

**База данных:**
- `deployments` - история деплоев (автоматическая регистрация через GitHub Actions)
- `bug_logs` - критические баги
- GitHub Issues API - интеграция с репозиторием

### 3. Telegram Bot Support

**Команды:**
- `/support` - меню поддержки
- `/bug` - форма подачи бага (FSM диалог)
- `/faq` - быстрые ответы

**Интеграции:**
- GitHub Issues API - автоматическое создание issues из багов
- База данных `bug_logs` - сохранение отчетов

### 4. Telegram Bot Admin Dashboard

**Команды:**
- `/morning` - утренний обзор: активные смены, критические баги, последний деплой
- `/devops` - DevOps панель: DORA метрики, GitHub Issues, статистика

**Доступ:** owner, superadmin

### 5. GitHub Actions CI/CD

**Workflow:** `.github/workflows/main.yml`

**Jobs:**
1. **test** - запуск pytest с coverage
2. **lint** - Black, flake8, mypy проверки
3. **security** - Safety, Bandit сканирование
4. **deploy** - автоматический деплой на production:
   - SSH подключение к серверу
   - Git pull + reset --hard
   - Docker Compose перезапуск
   - Health check
   - Регистрация деплоя в БД
5. **notify** - уведомление в Telegram о статусе

**Триггеры:** push в `main`, pull_request в `main`

## 🗄️ База данных

### Таблицы DevOps

```sql
-- Отчеты о багах
CREATE TABLE bug_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    what_doing TEXT NOT NULL,
    expected TEXT NOT NULL,
    actual TEXT NOT NULL,
    screenshot_url VARCHAR(500),
    priority VARCHAR(20) DEFAULT 'medium',  -- critical, high, medium, low
    status VARCHAR(20) DEFAULT 'open',      -- open, in_progress, resolved, closed
    github_issue_number INTEGER,
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- История деплоев
CREATE TABLE deployments (
    id SERIAL PRIMARY KEY,
    commit_sha VARCHAR(40) NOT NULL,
    commit_message TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20),        -- success, failed, rolled_back
    duration_seconds INTEGER,
    triggered_by VARCHAR(100), -- GitHub Actions, manual, etc
    tests_passed INTEGER,
    tests_failed INTEGER
);

-- Журнал архитектурных изменений
CREATE TABLE changelog_entries (
    id SERIAL PRIMARY KEY,
    date TIMESTAMPTZ DEFAULT NOW(),
    component VARCHAR(100) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    commit_sha VARCHAR(40),
    github_issue INTEGER,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    impact_score FLOAT,
    indexed_in_brain BOOLEAN DEFAULT FALSE
);

-- FAQ база знаний
CREATE TABLE faq_entries (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🔧 Конфигурация

### GitHub Integration

**Переменные окружения:**
```bash
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=Deniskada/staffprobot
```

**GitHub Secrets** (для CI/CD):
- `SSH_DEPLOY_KEY` - приватный SSH ключ для деплоя
- `TELEGRAM_BOT_TOKEN` - токен бота для уведомлений
- `TELEGRAM_CHAT_ID` - ID чата для уведомлений

**Настройка SSH ключа:**
1. Сгенерировать: `ssh-keygen -t ed25519 -C "github-actions-staffprobot-deploy"`
2. Добавить публичный ключ: `ssh-copy-id -i deploy_key.pub staffprobot@staffprobot.ru`
3. Добавить приватный ключ в GitHub Secrets

### Firewall на сервере

**Проблема:** SSH доступ ограничен определенными IP.

**Решение:** Разрешить SSH по ключу для всех:
```bash
sudo ufw allow 22/tcp comment "GitHub Actions deploy"
```

GitHub Actions использует динамические IP, поэтому безопасность обеспечивается через `authorized_keys`.

## 📈 DORA Metrics

### Deployment Frequency
```python
# Формула: количество деплоев за период / период (дни)
deployments_count / 30  # за 30 дней
```

### Change Failure Rate
```python
# Формула: (всего - успешные) / всего * 100
(dep-s_failed / deployments_count) * 100
```

### Lead Time for Changes
```python
# Расчет: started_at -> completed_at
# Реализован через duration_seconds
```

### Mean Time to Recovery (MTTR)
```python
# Расчет: среднее время восстановления после инцидента
# Реализован через incidents.timestamp
```

## 🚀 Использование

### Для пользователей

**Подать баг:**
1. Открыть `/support/bug`
2. Заполнить форму (что делал → что ожидал → что получил)
3. Выбрать приоритет
4. Баг автоматически создается в GitHub Issues

**Посмотреть баги:**
1. Открыть `/support/my-bugs`
2. Видеть статусы всех своих багов

**Поиск в FAQ:**
1. Открыть `/support/faq`
2. Фильтр по категориям
3. Поиск по вопросам

### Для разработчика

**Утренний обзор:**
```
/start -> /morning

📊 Утренний обзор
• Активных смен: 5
• Критических багов: 2
• Последний деплой: 2 часа назад
```

**DevOps панель:**
```
/start -> /devops

🖥 DevOps панель StaffProBot

📊 DORA Metrics (30 дней):
🚀 Deployment Frequency: 0.5/день
❌ Change Failure Rate: 20%

📈 Статистика деплоев:
• Всего: 15
• Успешных: 12
• Провалов: 3

🐛 GitHub Issues:
• Открытых: 8
• Критических: 2
```

**Веб-дашборд:**
```
Открыть: http://localhost:8001/admin/devops

Видно:
- DORA метрики (графики)
- Детальная статистика деплоев
- Список GitHub Issues
- Критические баги из БД
```

### Для CI/CD

**Автоматический деплой:**
1. Push в `main` → триггер GitHub Actions
2. Тесты + линтинг + безопасность
3. Деплой на production через SSH
4. Health check
5. Регистрация в БД
6. Уведомление в Telegram

## 📁 Структура кода

```
staffprobot/
├── apps/
│   ├── web/
│   │   ├── routes/
│   │   │   ├── support.py           # Support Hub
│   │   │   └── admin.py             # DevOps Dashboard
│   │   └── templates/
│   │       ├── support/
│   │       │   ├── hub.html         # Главная
│   │       │   ├── bug.html         # Форма бага
│   │       │   ├── faq.html         # FAQ
│   │       │   └── my_bugs.html     # Мои баги
│   │       └── admin/
│   │           └── devops.html      # DevOps панель
│   └── bot/
│       └── handlers_div/
│           ├── support_handlers.py  # /support, /bug, /faq
│           └── admin_handlers.py    # /morning, /devops
├── domain/
│   └── entities/
│       ├── bug_log.py               # BugLog модель
│       ├── deployment.py            # Deployment модель
│       ├── changelog_entry.py       # ChangelogEntry модель
│       └── faq_entry.py             # FAQEntry модель
├── apps/
│   └── web/
│       └── services/
│           └── github_service.py    # GitHub Issues API
├── .github/
│   └── workflows/
│       └── main.yml                 # CI/CD workflow
└── migrations/
    └── versions/
        └── 26f081e4388f_*.py        # DevOps таблицы
```

## 🔮 Будущее развитие

### Архитектура (опционально)
- AST парсинг кода для построения графа зависимостей
- Автоматическая визуализация архитектуры
- Расчет весов задач на основе связей

### Мониторинг (опционально)
- Prometheus метрики
- Grafana дашборды
- Алерты на критические метрики

### База знаний (опционально)
- Интеграция с Project Brain для RAG
- Автоматическое улучшение FAQ через обратную связь
- Chatbot поддержки с AI

## 📚 Документация

- [GitHub Actions Setup](GITHUB_ACTIONS_SETUP.md) - настройка CI/CD
- [Vision](vision.md) - архитектура проекта
- [Deployment Guide](DEPLOYMENT_PROCEDURE.md) - развертывание

## ✅ Статус реализации

- [x] Support Hub (веб-интерфейс)
- [x] Admin DevOps Dashboard
- [x] Telegram Bot Support
- [x] Telegram Bot Admin Dashboard
- [x] GitHub Actions CI/CD
- [x] Регистрация деплоев в БД
- [x] DORA Metrics Service
- [x] GitHub Issues Integration
- [ ] Architecture Parser (опционально)
- [ ] Architecture API (опционально)
- [ ] Prometheus Monitoring (опционально)
- [ ] AI-powered FAQ (опционально)

## 🎉 Итог

DevOps Command Center MVP реализован и готов к использованию. Система обеспечивает:
- Централизованную поддержку пользователей
- Автоматизацию CI/CD деплоев
- Мониторинг метрик разработки
- Интеграцию с GitHub Issues
- Dashboard для разработчика

Все критичные компоненты работают. Архитектурные визуализации и AI-улучшения могут быть добавлены позже при необходимости.

