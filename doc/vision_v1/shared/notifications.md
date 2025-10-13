# Система уведомлений (Shared)

> **Статус:** Активная система  
> **Версия:** 2.0 (Итерация 24)  
> **Админка:** Итерация 25

---

## 📋 Обзор

Система уведомлений StaffProBot обеспечивает надежную доставку сообщений через множественные каналы с поддержкой планирования, группировки и аналитики.

---

## 🏗 Архитектура

### Модели данных

#### Notification (Универсальная модель)
- **Файл:** `domain/entities/notification.py`
- **Таблица:** `notifications`
- **Назначение:** Основная модель для всех типов уведомлений

#### PaymentNotification (Специализированная)
- **Файл:** `domain/entities/payment_notification.py`
- **Таблица:** `payment_notifications`
- **Назначение:** Специализированные уведомления о платежах

### Сервисы

#### NotificationService (Основной)
- **Файл:** `shared/services/notification_service.py`
- **Назначение:** Создание, получение, управление уведомлениями
- **Кэширование:** Redis с TTL 5 минут

#### NotificationDispatcher (Диспетчер)
- **Файл:** `shared/services/notification_dispatcher.py`
- **Назначение:** Маршрутизация уведомлений по каналам

#### AdminNotificationService (Админка)
- **Файл:** `apps/web/services/admin_notification_service.py`
- **Назначение:** Аналитика и управление для суперадмина
- **Наследование:** Расширяет NotificationService

### Каналы доставки

#### Email
- **Файл:** `shared/services/senders/email_sender.py`
- **Технология:** SMTP через aiosmtplib
- **Статус:** ✅ Реализован

#### SMS
- **Файл:** `shared/services/senders/sms_sender.py`
- **Технология:** Twilio/SMSC/SmsAero
- **Статус:** ✅ Реализован

#### Push
- **Файл:** `shared/services/senders/push_sender.py`
- **Технология:** Web Push API через pywebpush
- **Статус:** ✅ Реализован

#### Telegram
- **Файл:** `shared/services/senders/telegram_sender.py`
- **Технология:** Telegram Bot API
- **Статус:** ✅ Реализован

---

## 📊 Типы уведомлений

### Смены
- `SHIFT_REMINDER` — Напоминание о смене
- `SHIFT_CONFIRMED` — Смена подтверждена
- `SHIFT_CANCELLED` — Смена отменена
- `SHIFT_STARTED` — Смена началась
- `SHIFT_COMPLETED` — Смена завершена

### Договоры
- `CONTRACT_SIGNED` — Договор подписан
- `CONTRACT_TERMINATED` — Договор расторгнут
- `CONTRACT_EXPIRING` — Договор истекает
- `CONTRACT_UPDATED` — Договор обновлен

### Отзывы
- `REVIEW_RECEIVED` — Получен отзыв
- `REVIEW_MODERATED` — Отзыв промодерирован
- `APPEAL_SUBMITTED` — Подано обжалование
- `APPEAL_DECISION` — Решение по обжалованию

### Платежи
- `PAYMENT_DUE` — Предстоящий платеж
- `PAYMENT_SUCCESS` — Успешный платеж
- `PAYMENT_FAILED` — Неудачный платеж
- `SUBSCRIPTION_EXPIRING` — Подписка истекает
- `SUBSCRIPTION_EXPIRED` — Подписка истекла
- `USAGE_LIMIT_WARNING` — Предупреждение о лимите
- `USAGE_LIMIT_EXCEEDED` — Лимит превышен

### Системные
- `WELCOME` — Приветствие
- `PASSWORD_RESET` — Сброс пароля
- `ACCOUNT_SUSPENDED` — Аккаунт заблокирован
- `ACCOUNT_ACTIVATED` — Аккаунт активирован
- `SYSTEM_MAINTENANCE` — Системное обслуживание
- `FEATURE_ANNOUNCEMENT` — Анонс новой функции

---

## 🔄 Статусы уведомлений

- `PENDING` — Ожидает отправки
- `SENT` — Отправлено
- `DELIVERED` — Доставлено
- `FAILED` — Не удалось отправить
- `READ` — Прочитано
- `CANCELLED` — Отменено

---

## 📱 Каналы доставки

- `EMAIL` — Email
- `SMS` — SMS
- `PUSH` — Web Push
- `TELEGRAM` — Telegram
- `IN_APP` — В приложении
- `WEBHOOK` — Webhook
- `SLACK` — Slack
- `DISCORD` — Discord

---

## ⚡ Приоритеты

- `LOW` — Низкий (дайджесты, новости)
- `NORMAL` — Обычный (большинство уведомлений)
- `HIGH` — Высокий (важные события)
- `URGENT` — Срочный (критичные, не ограничиваются rate limit)

---

## 🛠 API Endpoints

### Пользовательские API
```
GET    /api/notifications                   # Список уведомлений пользователя
GET    /api/notifications/unread/count      # Количество непрочитанных
POST   /api/notifications/{id}/read         # Отметить прочитанным
POST   /api/notifications/read-all          # Отметить все прочитанными
DELETE /api/notifications/{id}              # Удалить уведомление

GET    /api/notifications/preferences       # Получить настройки
POST   /api/notifications/preferences       # Обновить настройки
POST   /api/notifications/push/subscribe    # Подписаться на Push
POST   /api/notifications/push/unsubscribe  # Отписаться от Push
```

### Админские API
```
GET    /admin/notifications/                # Дашборд уведомлений
GET    /admin/notifications/list            # Список всех уведомлений
GET    /admin/notifications/analytics       # Детальная аналитика
GET    /admin/notifications/templates      # Управление шаблонами
GET    /admin/notifications/settings       # Настройки каналов

POST   /admin/api/notifications/bulk/cancel # Отмена уведомлений
POST   /admin/api/notifications/bulk/retry  # Повторная отправка
POST   /admin/api/notifications/bulk/delete # Удаление уведомлений
POST   /admin/api/notifications/bulk/export # Экспорт уведомлений
POST   /admin/api/notifications/test        # Тестовая отправка
```

---

## 📝 Шаблоны

### Расположение
- **Файлы:** `shared/templates/notifications/`
- **Базовый класс:** `shared/templates/notifications/base_templates.py`

### Переменные
- `{{user_name}}` — Имя пользователя
- `{{object_name}}` — Название объекта
- `{{shift_date}}` — Дата смены
- `{{contract_number}}` — Номер договора
- `{{review_rating}}` — Рейтинг отзыва

### Форматы
- **HTML** — для Email канала
- **Plain Text** — для SMS, Telegram, Push
- **Markdown** — для Telegram (опционально)

---

## ⚙️ Настройки каналов

### Email (SMTP)
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@staffprobot.ru
SMTP_PASSWORD=***
SMTP_FROM=StaffProBot <notifications@staffprobot.ru>
```

### SMS (Twilio)
```bash
TWILIO_ACCOUNT_SID=***
TWILIO_AUTH_TOKEN=***
TWILIO_PHONE_NUMBER=+7...
```

### Push (VAPID)
```bash
VAPID_PUBLIC_KEY=***
VAPID_PRIVATE_KEY=***
VAPID_SUBJECT=mailto:admin@staffprobot.ru
```

### Telegram (Bot)
```bash
TELEGRAM_BOT_TOKEN=***
TELEGRAM_WEBHOOK_URL=https://staffprobot.ru/webhook/telegram
```

---

## 📊 Аналитика

### Метрики
- **Delivery Rate** — процент доставки по каналам
- **Read Rate** — процент прочтения по типам
- **Error Rate** — процент ошибок и их причины
- **Response Time** — время отклика каналов

### Отчеты
- Статистика по периодам (день, неделя, месяц)
- Топ пользователей по активности
- Анализ эффективности каналов
- Тренды доставки и прочтения

---

## 🔒 Безопасность

### Rate Limiting
- **Обычные уведомления:** 10/час на пользователя
- **Срочные уведомления:** без ограничений
- **Массовые операции:** 100/час на админа

### Валидация
- Проверка email адресов
- Валидация телефонных номеров
- Санитизация содержимого сообщений

### Логирование
- Все операции создания/отправки
- Ошибки доставки с контекстом
- Админские действия

---

## 🧪 Тестирование

### Unit тесты
- **Файлы:** `tests/unit/test_notification_service.py`
- **Покрытие:** > 90%
- **Моки:** внешние сервисы (SMTP, SMS, Push)

### Integration тесты
- **Файлы:** `tests/integration/test_notifications.py`
- **Сценарии:** полный цикл создания → отправки → чтения

### E2E тесты
- Реальная отправка в тестовом режиме
- Проверка доставки по всем каналам
- Тестирование админской панели

---

## 📈 Мониторинг

### Метрики Prometheus
- `notifications_created_total` — создано уведомлений
- `notifications_sent_total` — отправлено уведомлений
- `notifications_delivered_total` — доставлено уведомлений
- `notifications_failed_total` — неудачных отправок
- `notification_delivery_duration_seconds` — время доставки

### Алерты
- Высокий процент ошибок (> 5%)
- Медленная доставка (> 30 сек)
- Недоступность каналов
- Превышение rate limit

---

## 🔧 Troubleshooting

### Частые проблемы

#### Медленная доставка
```bash
# Проверка очереди Celery
docker compose -f docker-compose.prod.yml exec celery-worker celery -A core.celery.celery_app inspect active

# Проверка Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory
```

#### Ошибки SMTP
```bash
# Проверка настроек SMTP
docker compose -f docker-compose.prod.yml exec web python -c "
from shared.services.senders.email_sender import EmailNotificationSender
sender = EmailNotificationSender()
print(sender.test_connection())
"
```

#### Проблемы с Push
```bash
# Проверка VAPID ключей
docker compose -f docker-compose.prod.yml exec web python -c "
from shared.services.senders.push_sender import PushNotificationSender
sender = PushNotificationSender()
print(sender.validate_vapid_keys())
"
```

---

## 📚 Документация

- **[Итерация 24](../plans/iteration24/README.md)** — Основная система уведомлений
- **[Итерация 25](../plans/iteration25/README.md)** — Админская панель управления
- **[Техническое руководство](../plans/iteration25/TECHNICAL_GUIDE.md)** — Детальная техническая документация

---

## 🚀 Развитие

### Планируемые улучшения
- A/B тестирование шаблонов
- Интеграция с Slack/Discord
- Система отписки через токены
- Машинное обучение для оптимизации времени отправки
- Геотаргетинг уведомлений

### Обратная связь
- **Issues:** Создавайте задачи в репозитории
- **Feature Requests:** Предлагайте новые функции
- **Bug Reports:** Сообщайте об ошибках с логами

---

**Система уведомлений StaffProBot — надежная доставка сообщений для всех! 🔔**
