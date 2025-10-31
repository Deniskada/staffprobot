# Iteration 39: Анализ биллинга и план интеграции с YooKassa

## Анализ существующей системы биллинга

### Целевая аудитория

**Биллинг предназначен ДЛЯ ВЛАДЕЛЬЦЕВ (owners), НЕ для сотрудников.**

Доказательства:
1. **`BillingService.update_usage_metrics()`** использует `Object.owner_id == user_id` для подсчёта объектов
2. **`UsageMetrics`** считает метрики для владельца: объекты (`current_objects`), сотрудники (`current_employees`), управляющие (`current_managers`)
3. **`UserSubscription`** - подписки владельцев на тарифные планы (`TariffPlan`)
4. Все роуты биллинга требуют роль `owner` или `superadmin`

### Структура биллинга

#### 1. Сущности БД:

**`BillingTransaction`** (`domain/entities/billing_transaction.py`):
- `user_id` - владелец (ForeignKey → users)
- `subscription_id` - подписка (ForeignKey → user_subscriptions)
- `transaction_type`: PAYMENT, REFUND, CREDIT, DEBIT, ADJUSTMENT
- `status`: PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED, REFUNDED
- `payment_method`: CARD, BANK_TRANSFER, CASH, MANUAL, **STRIPE, YOOKASSA** ✅ (уже есть в enum!)
- `amount`, `currency` (RUB)
- `external_id` - ID в платежной системе
- `gateway_response` - ответ от платежного шлюза
- `expires_at` - срок действия платежа

**`UserSubscription`** (`domain/entities/user_subscription.py`):
- `user_id` - владелец (ForeignKey → users)
- `tariff_plan_id` - тарифный план (ForeignKey → tariff_plans)
- `status`: ACTIVE, EXPIRED, CANCELLED, SUSPENDED
- `started_at`, `expires_at`, `last_payment_at`
- `auto_renewal` - автоматическое продление
- `payment_method` - способ оплаты (строка)

**`UsageMetrics`** (`domain/entities/usage_metrics.py`):
- Метрики использования: объекты, сотрудники, управляющие
- Лимиты из тарифного плана
- Процент использования
- Проверка превышений лимитов

**`PaymentNotification`** (`domain/entities/payment_notification.py`):
- Отдельная таблица для уведомлений о платежах (НЕ через общую систему `Notification`)
- Связана с `BillingTransaction` и `UserSubscription`

#### 2. Сервисы:

**`BillingService`** (`apps/web/services/billing_service.py`):
- ✅ `create_transaction()` - создание транзакции
- ✅ `update_transaction_status()` - обновление статуса
- ✅ `get_user_transactions()` - список транзакций пользователя
- ✅ `update_usage_metrics()` - обновление метрик использования
- ✅ `check_usage_limits()` - проверка лимитов
- ✅ `create_payment_notification()` - создание уведомлений о платежах
- ✅ `schedule_subscription_renewal_notifications()` - планирование уведомлений о продлении
- ⚠️ `process_auto_renewal()` - автообновление подписки (TODO: интеграция с платежной системой)

#### 3. Роуты:

**`/admin/billing/*`** (`apps/web/routes/billing.py`):
- Только для суперадмина (`require_superadmin`)
- Дашборд биллинга
- Список транзакций
- Метрики использования
- Обновление статуса транзакций (ручное)

**`/admin/tariffs/*`** (`apps/web/routes/tariffs.py`):
- Только для суперадмина
- CRUD тарифных планов

**`/admin/user_subscriptions/*`** (`apps/web/routes/user_subscriptions.py`):
- Только для суперадмина
- Назначение подписок владельцам (assign_subscription)

### Что отсутствует

#### 1. Интеграция с платежными шлюзами:
- ❌ Нет SDK YooKassa
- ❌ Нет создания платежей через YooKassa
- ❌ Нет обработки вебхуков от YooKassa
- ❌ Нет обработки статусов платежей (success, failed, pending)

#### 2. Роуты для владельцев:
- ❌ Нет страницы выбора тарифного плана для владельца (`/owner/tariffs`)
- ❌ Нет страницы оплаты подписки (`/owner/subscription/pay`)
- ❌ Нет истории транзакций владельца (`/owner/billing/transactions`)
- ❌ Нет страницы управления подпиской (`/owner/subscription`)

#### 3. Обработка платежей:
- ❌ Нет роута для вебхуков от YooKassa (`/api/webhooks/yookassa`)
- ❌ Нет логики создания платежей через YooKassa API
- ❌ Нет обработки статусов платежей (success, failed, cancelled)
- ❌ Нет обновления подписки после успешной оплаты

#### 4. Уведомления:
- ❌ Нет уведомлений `SUBSCRIPTION_EXPIRING` и `SUBSCRIPTION_EXPIRED` (Iteration 38, будут в Iteration 39+)

## План интеграции с YooKassa (Iteration 39)

### Фаза 1: Установка и настройка SDK YooKassa (0.5 дня)

**1.1. Установка SDK**
- Добавить `yookassa` в `requirements.txt`
- Версия: `3.x` (последняя стабильная)

**1.2. Настройка переменных окружения**
- `YOOKASSA_SHOP_ID` - ID магазина
- `YOOKASSA_SECRET_KEY` - секретный ключ
- `YOOKASSA_WEBHOOK_SECRET` - секрет для проверки вебхуков
- `YOOKASSA_TEST_MODE` - режим тестирования (sandbox)

**1.3. Создание сервиса YooKassa**
- Файл: `apps/web/services/payment_gateway/yookassa_service.py`
- Класс: `YooKassaService`
- Методы:
  - `create_payment()` - создание платежа через YooKassa API
  - `get_payment_status()` - получение статуса платежа
  - `verify_webhook()` - проверка подлинности вебхука

### Фаза 2: Создание платежей для владельцев (1 день)

**2.1. Роуты для владельцев**
- Файл: `apps/web/routes/owner_subscription.py` (новый)
- Роуты:
  - `GET /owner/tariffs` - список тарифных планов для выбора
  - `GET /owner/subscription` - текущая подписка владельца
  - `POST /owner/subscription/subscribe` - создание платежа для подписки
  - `GET /owner/billing/transactions` - история транзакций владельца

**2.2. Интеграция YooKassa в создание платежа**
- При создании `BillingTransaction` вызывать `YooKassaService.create_payment()`
- Сохранять `external_id` (payment ID от YooKassa) в `BillingTransaction.external_id`
- Возвращать URL оплаты для редиректа владельца
- Статус транзакции: `PENDING` → `PROCESSING`

**2.3. Шаблоны для владельцев**
- `owner/tariffs.html` - выбор тарифного плана
- `owner/subscription.html` - управление подпиской
- `owner/billing/transactions.html` - история транзакций

### Фаза 3: Обработка вебхуков от YooKassa (1.5 дня)

**3.1. Роут для вебхуков**
- Файл: `apps/web/routes/webhooks.py` (новый)
- Роут: `POST /api/webhooks/yookassa`
- Проверка подлинности через `verify_webhook()`
- Обработка событий:
  - `payment.succeeded` - успешная оплата
  - `payment.canceled` - отменённая оплата
  - `payment.waiting_for_capture` - ожидание подтверждения
  - `refund.succeeded` - успешный возврат

**3.2. Обработка статусов платежей**
- При `payment.succeeded`:
  - Обновить `BillingTransaction.status = COMPLETED`
  - Если есть `subscription_id`, обновить `UserSubscription`:
    - Установить `status = ACTIVE`
    - Установить `expires_at` (started_at + billing_period)
    - Установить `last_payment_at`
  - Создать уведомление владельцу (`PAYMENT_SUCCESS`)

- При `payment.canceled`:
  - Обновить `BillingTransaction.status = CANCELLED`
  - Создать уведомление владельцу (`PAYMENT_FAILED`)

**3.3. Защита от дубликатов**
- Проверять `external_id` перед обработкой вебхука
- Идемпотентность: один вебхук не должен обрабатываться дважды
- Логирование всех вебхуков для отладки

### Фаза 4: Автоматическое продление подписок (1 день)

**4.1. Celery задача для проверки истекающих подписок**
- Файл: `core/celery/tasks/billing_tasks.py` (новый)
- Задача: `check_expiring_subscriptions`
- Запуск: ежедневно в 09:00 UTC
- Логика:
  - Найти подписки, истекающие через 7 дней и 1 день
  - Создать уведомления `SUBSCRIPTION_EXPIRING` (Iteration 38)
  - Для подписок с `auto_renewal=True` создать транзакцию для продления

**4.2. Автоматическое создание платежа**
- При создании транзакции для автопродления вызывать `YooKassaService.create_payment()`
- Сохранять ссылку на оплату в `gateway_response`
- Отправлять уведомление владельцу о необходимости оплаты

**4.3. Обработка истёкших подписок**
- Celery задача: `check_expired_subscriptions` (ежедневно в 00:05 UTC)
- Обновить `UserSubscription.status = EXPIRED` для истёкших
- Создать уведомление `SUBSCRIPTION_EXPIRED` (Iteration 38)

### Фаза 5: UI для владельцев (1 день)

**5.1. Страница выбора тарифа**
- Список доступных тарифных планов
- Сравнение тарифов (таблица)
- Кнопка "Выбрать тариф" → переход к оплате
- Информация о текущей подписке (если есть)

**5.2. Страница управления подпиской**
- Текущая подписка: тариф, срок действия, статус
- Кнопка "Продлить подписку"
- Настройка автопродления
- История платежей

**5.3. Страница оплаты**
- Форма с реквизитами (если нужна)
- Редирект на страницу оплаты YooKassa
- После оплаты: редирект обратно с проверкой статуса

### Фаза 6: Тестирование и документация (0.5 дня)

**6.1. Тестирование в sandbox**
- Создание тестового платежа
- Обработка вебхуков (succeeded, canceled)
- Автоматическое продление подписки
- Проверка идемпотентности вебхуков

**6.2. Документация**
- Обновить `DOCUMENTATION_RULES.md` с новыми роутами
- Создать `doc/vision_v1/features/billing_yookassa_integration.md`
- Обновить `roadmap.md` (Iteration 39)

## Итого по Iteration 39:

**Длительность:** 5 дней  
**Приоритет:** Критический  
**Результат:**
- ✅ Интеграция с YooKassa для приёма оплат от владельцев
- ✅ Автоматическое создание платежей при выборе тарифа
- ✅ Обработка вебхуков от YooKassa
- ✅ Обновление подписок после успешной оплаты
- ✅ UI для владельцев по управлению подписками
- ✅ Автоматическое продление подписок (через Celery)
- ✅ Уведомления о платежах и истечении подписок

**DoD:**
- [ ] YooKassa SDK установлен и настроен
- [ ] Роуты для владельцев созданы и работают
- [ ] Вебхуки обрабатываются корректно
- [ ] Автопродление работает
- [ ] Протестировано в sandbox YooKassa
- [ ] Документация создана
- [ ] Задеплоено на production (после тестирования)

**Файлы для создания:**
- `apps/web/services/payment_gateway/yookassa_service.py`
- `apps/web/routes/owner_subscription.py`
- `apps/web/routes/webhooks.py`
- `core/celery/tasks/billing_tasks.py`
- `apps/web/templates/owner/tariffs.html`
- `apps/web/templates/owner/subscription.html`
- `apps/web/templates/owner/billing/transactions.html`

**Файлы для изменения:**
- `apps/web/services/billing_service.py` - интеграция YooKassa
- `apps/web/routes/billing.py` - возможно добавить роуты для владельцев
- `core/celery/celery_app.py` - добавить задачи в beat_schedule
- `requirements.txt` - добавить `yookassa`
- `.env.example` - добавить переменные YooKassa

**Celery конфигурация:**
- `check-expiring-subscriptions` - ежедневно в 09:00 UTC
- `check-expired-subscriptions` - ежедневно в 00:05 UTC

