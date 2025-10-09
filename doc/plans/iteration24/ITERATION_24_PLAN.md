# 🎯 Итерация 24: Система уведомлений

**Основано на:** Итерация 10 из roadmap.md  
**Статус:** В планировании  
**Сроки:** 2-3 недели  
**Приоритет:** Высокий

---

## 📋 Описание

Разработка полнофункциональной системы уведомлений с поддержкой множественных каналов доставки (Email, SMS, Push, Telegram), настройками пользователей, шаблонами, расписанием и аналитикой.

### Текущее состояние

✅ **Уже реализовано:**
- Базовая таблица `notifications` в БД
- Модель `PaymentNotification` для платежных уведомлений
- Celery задачи для асинхронной отправки
- Telegram напоминания о сменах через `ReminderScheduler`
- Шаблоны уведомлений для отзывов (`ReviewNotificationTemplates`)
- Временно отключенный `NotificationService`

❌ **Требуется:**
- Восстановление и расширение `NotificationService`
- Email канал доставки
- SMS канал доставки
- Push уведомления в браузере
- Система настроек уведомлений для пользователей
- Универсальные шаблоны уведомлений
- Расписание и группировка уведомлений
- Аналитика и отчеты

---

## 🎯 Задачи

### **Фаза 1: Основа системы (3-4 дня)**

#### 1.1. Создать единую модель уведомлений (1 день)
**Files:** `domain/entities/notification.py`, `migrations/versions/*`

**Задачи:**
- [x] Создать модель `Notification` (универсальная для всех типов)
- [ ] Добавить поля: `user_id`, `type`, `channel`, `status`, `title`, `message`, `data`, `priority`
- [ ] Добавить временные метки: `created_at`, `scheduled_at`, `sent_at`, `read_at`
- [ ] Создать enum `NotificationType` (shift, contract, review, payment, system)
- [ ] Создать enum `NotificationPriority` (low, normal, high, urgent)
- [ ] Создать миграцию Alembic

**Acceptance:**
- Модель поддерживает все типы уведомлений
- Индексы по `user_id`, `status`, `created_at`
- Миграция применяется без ошибок

---

#### 1.2. Восстановить NotificationService (2 дня)
**Files:** `shared/services/notification_service.py`

**Задачи:**
- [ ] Удалить временные заглушки
- [ ] Реализовать `create_notification(user_id, type, channel, title, message, data)`
- [ ] Реализовать `get_user_notifications(user_id, filters)`
- [ ] Реализовать `mark_as_read(notification_id)` / `mark_all_as_read(user_id)`
- [ ] Реализовать `get_unread_count(user_id)`
- [ ] Добавить группировку похожих уведомлений
- [ ] Добавить приоритизацию
- [ ] Интегрировать с Redis кэшированием (@cached декоратор)

**Acceptance:**
- Все методы работают корректно
- Уведомления кэшируются (TTL 5 мин)
- Инвалидация кэша при создании/чтении

---

#### 1.3. Создать систему шаблонов (1 день)
**Files:** `shared/templates/notifications/base_templates.py`

**Задачи:**
- [ ] Создать `NotificationTemplateManager`
- [ ] Шаблоны для смен: `shift_reminder`, `shift_confirmed`, `shift_cancelled`
- [ ] Шаблоны для договоров: `contract_signed`, `contract_terminated`, `contract_expiring`
- [ ] Шаблоны для отзывов: `review_received`, `review_moderated`, `appeal_decision`
- [ ] Шаблоны для платежей: `payment_due`, `payment_success`, `payment_failed`
- [ ] Шаблоны системные: `welcome`, `password_reset`, `account_suspended`
- [ ] Поддержка переменных в шаблонах (`{{user_name}}`, `{{object_name}}`)
- [ ] Рендеринг шаблонов для разных каналов (HTML для email, plain text для SMS/Telegram)

**Acceptance:**
- Шаблоны рендерятся корректно
- Переменные заменяются на реальные значения
- Поддержка HTML и plain text

---

### **Фаза 2: Каналы доставки (4-5 дней)**

#### 2.1. Email уведомления (2 дня)
**Files:** `core/notifications/email_channel.py`, `requirements.txt`

**Задачи:**
- [ ] Добавить зависимости: `aiosmtplib`, `email-validator`
- [ ] Создать `EmailChannel` класс
- [ ] Настроить SMTP через переменные окружения (`.env`)
- [ ] Реализовать `send_email(to, subject, html, plain_text)`
- [ ] Добавить поддержку вложений
- [ ] Создать HTML шаблоны писем (Jinja2)
- [ ] Добавить fallback на plain text
- [ ] Обработка ошибок отправки
- [ ] Логирование всех отправок

**Acceptance:**
- Email отправляются успешно
- HTML письма корректно отображаются
- Ошибки SMTP обрабатываются gracefully

---

#### 2.2. SMS уведомления (1 день)
**Files:** `core/notifications/sms_channel.py`

**Задачи:**
- [ ] Создать `SMSChannel` класс
- [ ] Интеграция с SMS провайдером (Twilio / SMSC.ru / SmsAero)
- [ ] Настройки через переменные окружения
- [ ] Реализовать `send_sms(phone, message)`
- [ ] Валидация номеров телефонов
- [ ] Обработка ошибок API
- [ ] Rate limiting для SMS
- [ ] Логирование отправок

**Acceptance:**
- SMS отправляются через выбранный провайдер
- Номера валидируются
- Ошибки API обрабатываются

---

#### 2.3. Push уведомления (1-2 дня)
**Files:** `core/notifications/push_channel.py`, `apps/web/static/js/push_notifications.js`

**Задачи:**
- [ ] Добавить зависимость: `pywebpush`
- [ ] Создать `PushChannel` класс
- [ ] Реализовать Web Push API
- [ ] Создать Service Worker для браузера (`sw.js`)
- [ ] JavaScript для подписки на уведомления
- [ ] Сохранение subscription в БД
- [ ] Отправка push через `pywebpush`
- [ ] Обработка отписок
- [ ] UI кнопка "Разрешить уведомления"

**Acceptance:**
- Push уведомления работают в Chrome/Firefox/Edge
- Пользователь может подписаться/отписаться
- Уведомления приходят в браузер

---

#### 2.4. Улучшение Telegram канала (0.5 дня)
**Files:** `core/notifications/telegram_channel.py`

**Задачи:**
- [ ] Создать `TelegramChannel` класс (обертка над ботом)
- [ ] Унифицировать с другими каналами
- [ ] Поддержка форматирования (HTML/Markdown)
- [ ] Inline кнопки в уведомлениях
- [ ] Обработка ошибок отправки

**Acceptance:**
- Telegram уведомления через единый интерфейс
- Форматирование работает
- Inline кнопки отображаются

---

### **Фаза 3: Настройки пользователей (2 дня)**

#### 3.1. Модель настроек уведомлений (1 день)
**Files:** `domain/entities/notification_preferences.py`, `migrations/versions/*`

**Задачи:**
- [ ] Создать модель `NotificationPreferences`
- [ ] Поля: `user_id`, `notification_type`, `channels` (JSON: email, sms, telegram, push)
- [ ] Поле `enabled` для полного отключения типа
- [ ] Поле `frequency` (instant, hourly_digest, daily_digest)
- [ ] Создать миграцию

**Acceptance:**
- Пользователь может настроить каналы для каждого типа
- Настройки сохраняются в БД

---

#### 3.2. UI страница настроек (1 день)
**Files:** `apps/web/templates/shared/notification_settings.html`, `apps/web/routes/notifications.py`

**Задачи:**
- [ ] Создать страницу `/settings/notifications`
- [ ] Таблица с типами уведомлений и чекбоксами каналов
- [ ] Переключатель "Включить/Выключить" для каждого типа
- [ ] Выбор частоты (мгновенно, раз в час, раз в день)
- [ ] API endpoint `POST /api/notifications/preferences`
- [ ] Сохранение настроек

**Acceptance:**
- Пользователь видит все типы уведомлений
- Настройки сохраняются и применяются
- UI интуитивен и понятен

---

### **Фаза 4: Расписание и группировка (2 дня)**

#### 4.1. Планировщик уведомлений (1 день)
**Files:** `core/celery/tasks/notification_scheduler.py`

**Задачи:**
- [ ] Celery задача `process_scheduled_notifications` (каждые 5 минут)
- [ ] Отправка уведомлений с `scheduled_at <= now` и `status = pending`
- [ ] Обновление статуса на `sent` / `failed`
- [ ] Повторные попытки при ошибках (retry logic)
- [ ] Логирование отправок

**Acceptance:**
- Запланированные уведомления отправляются вовремя
- Ошибки ретраятся
- Статусы обновляются

---

#### 4.2. Группировка и дайджесты (1 день)
**Files:** `shared/services/notification_service.py`

**Задачи:**
- [ ] Метод `create_digest(user_id, period)` - группировка за период
- [ ] Объединение похожих уведомлений (одинаковый тип + объект)
- [ ] Генерация дайджеста (HTML/text)
- [ ] Celery задача `send_hourly_digests` и `send_daily_digests`
- [ ] Настройка через `NotificationPreferences.frequency`

**Acceptance:**
- Дайджесты отправляются согласно настройкам
- Уведомления группируются корректно
- Email дайджест красиво оформлен

---

### **Фаза 5: Аналитика и отчеты (2 дня)**

#### 5.1. Статистика уведомлений (1 день)
**Files:** `shared/services/notification_analytics.py`, `apps/web/routes/admin.py`

**Задачи:**
- [ ] Метод `get_notification_stats(date_from, date_to, filters)`
- [ ] Метрики: отправлено, доставлено, прочитано, ошибки
- [ ] Группировка по типам, каналам, периодам
- [ ] Calculation: delivery rate, read rate, error rate
- [ ] Экспорт в JSON/CSV

**Acceptance:**
- Статистика корректна
- Экспорт работает
- Метрики полезны для анализа

---

#### 5.2. UI страница аналитики (1 день)
**Files:** `apps/web/templates/admin/notification_analytics.html`

**Задачи:**
- [ ] Страница `/admin/notifications/analytics` (только admin)
- [ ] Графики: отправлено по дням, по типам, по каналам
- [ ] Таблица с ошибками доставки
- [ ] Фильтры: дата, тип, канал, статус
- [ ] Кнопка экспорта в CSV

**Acceptance:**
- Графики отображаются корректно
- Фильтры работают
- Экспорт скачивается

---

### **Фаза 6: Дополнительные функции (2 дня)**

#### 6.1. A/B тестирование шаблонов (опционально, 1 день)
**Files:** `shared/services/ab_testing_service.py`

**Задачи:**
- [ ] Модель `NotificationABTest`
- [ ] Разделение пользователей на группы (A/B)
- [ ] Отправка разных шаблонов
- [ ] Трекинг: click rate, read rate
- [ ] Определение победителя

**Acceptance:**
- A/B тесты создаются и запускаются
- Метрики собираются
- Победитель определяется автоматически

---

#### 6.2. Интеграции (Slack, Discord) (опционально, 1 день)
**Files:** `core/notifications/slack_channel.py`, `core/notifications/discord_channel.py`

**Задачи:**
- [ ] Slack webhook интеграция
- [ ] Discord webhook интеграция
- [ ] Форматирование для каждой платформы
- [ ] Настройки в системных настройках

**Acceptance:**
- Уведомления приходят в Slack/Discord
- Форматирование корректное

---

#### 6.3. Система отписки (0.5 дня)
**Files:** `apps/web/routes/notifications.py`

**Задачи:**
- [ ] Endpoint `GET /unsubscribe/{token}`
- [ ] Генерация unsubscribe токена для email
- [ ] Страница подтверждения отписки
- [ ] Обновление `NotificationPreferences`

**Acceptance:**
- Пользователь может отписаться от email через ссылку
- Настройки обновляются

---

#### 6.4. Защита от спама (0.5 дня)
**Files:** `core/utils/notification_rate_limiter.py`

**Задачи:**
- [ ] Rate limiting: max 10 уведомлений/час на пользователя
- [ ] Исключения для urgent уведомлений
- [ ] Логирование превышений лимита
- [ ] Уведомление админа при спаме

**Acceptance:**
- Лимиты соблюдаются
- Urgent уведомления не ограничиваются
- Спам детектится

---

### **Фаза 7: Тестирование и документация (2 дня)**

#### 7.1. Unit тесты (1 день)
**Files:** `tests/unit/test_notification_service.py`, `tests/unit/test_channels.py`

**Задачи:**
- [ ] Тесты NotificationService
- [ ] Тесты каждого канала (mock API)
- [ ] Тесты шаблонов
- [ ] Тесты планировщика
- [ ] Тесты группировки

**Acceptance:**
- Покрытие тестами 90%+
- Все тесты проходят

---

#### 7.2. Integration тесты (0.5 дня)
**Files:** `tests/integration/test_notification_flow.py`

**Задачи:**
- [ ] Тест полного цикла: создание → отправка → чтение
- [ ] Тест дайджестов
- [ ] Тест настроек пользователей
- [ ] Тест ошибок и ретраев

**Acceptance:**
- Интеграционные тесты проходят
- Покрыты основные сценарии

---

#### 7.3. Документация (0.5 дня)
**Files:** `doc/vision_v1/shared/notifications.md`, `doc/plans/roadmap.md`

**Задачи:**
- [ ] Описание системы уведомлений
- [ ] API endpoints
- [ ] Конфигурация каналов
- [ ] Примеры использования
- [ ] Обновить roadmap (итерация 24 завершена)

**Acceptance:**
- Документация соответствует `DOCUMENTATION_RULES.md`
- Все API задокументированы

---

## 📊 Метрики успеха

- ✅ Уведомления доставляются через 4+ канала
- ✅ Пользователи могут настраивать предпочтения
- ✅ Дайджесты группируют уведомления
- ✅ Email/SMS/Push/Telegram работают стабильно
- ✅ Аналитика показывает delivery rate > 95%
- ✅ Тесты покрывают 90%+ кода
- ✅ Документация актуальна

---

## 🔗 Зависимости

**Новые библиотеки:**
```
aiosmtplib>=3.0.0
email-validator>=2.0.0
pywebpush>=1.14.0
twilio>=8.0.0  # или smsc / smsaero
jinja2>=3.1.0  # уже есть
```

**Переменные окружения:**
```
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@staffprobot.ru
SMTP_PASSWORD=***
SMTP_FROM=StaffProBot <notifications@staffprobot.ru>

# SMS (Twilio)
TWILIO_ACCOUNT_SID=***
TWILIO_AUTH_TOKEN=***
TWILIO_PHONE_NUMBER=+7...

# Push (VAPID)
VAPID_PUBLIC_KEY=***
VAPID_PRIVATE_KEY=***
VAPID_SUBJECT=mailto:admin@staffprobot.ru
```

---

## 🚀 Порядок реализации

1. **Фаза 1** (основа) → **Фаза 2** (каналы) → **Фаза 3** (настройки)
2. **Фаза 4** (расписание) → **Фаза 5** (аналитика)
3. **Фаза 6** (опциональные функции) → **Фаза 7** (тесты/документация)

**Критический путь:** 1 → 2 → 3 → 7  
**Опциональные:** 6.1, 6.2 (A/B тесты, интеграции)

---

## 📝 Примечания

- Telegram канал уже работает - нужно только унифицировать
- Email обязателен для восстановления пароля
- SMS опционален (требует платной подписки у провайдера)
- Push требует HTTPS на проде
- Rate limiting важен для защиты от спама

