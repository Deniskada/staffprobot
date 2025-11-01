# План Smoke-тестирования Iteration 39: Биллинг и интеграция с YooKassa

## Цель тестирования

Проверить корректность работы всех аспектов интеграции биллинга с YooKassa:
- Создание платежей через YooKassa
- Обработка вебхуков
- Автопродление подписок
- Назначение подписок админом
- Управление подписками владельцами

---

## Подготовка к тестированию

### 1. Настройка тестового окружения YooKassa

1. **Создать тестовый магазин в YooKassa:**
   - Перейти на https://yookassa.ru/
   - Войти в личный кабинет
   - Создать тестовый магазин (или использовать существующий)
   - Получить `Shop ID` и `Secret Key` для тестового режима

2. **Настроить переменные окружения:**
   ```bash
   # В .env файле (dev)
   YOOKASSA_SHOP_ID=ваш_shop_id
   YOOKASSA_SECRET_KEY=ваш_secret_key
   YOOKASSA_WEBHOOK_SECRET=опционально_для_проверки_подлинности
   YOOKASSA_TEST_MODE=true
   ```

3. **Настроить вебхуки YooKassa:**
   - В личном кабинете YooKassa перейти в раздел "Настройки" → "HTTP-уведомления"
   - Указать URL: `https://ваш-домен.ru/api/webhooks/yookassa` (или `http://localhost:8001/api/webhooks/yookassa` для dev)
   - Выбрать события: `payment.succeeded`, `payment.canceled`, `payment.waiting_for_capture`

4. **Установить зависимости:**
   ```bash
   docker compose -f docker-compose.dev.yml exec web pip install yookassa
   docker compose -f docker-compose.dev.yml restart web
   ```

5. **Применить миграции (если есть):**
   ```bash
   docker compose -f docker-compose.dev.yml exec web alembic upgrade head
   ```

---

## Сценарии тестирования

### Сценарий 1: Смена тарифа владельцем (платный тариф)

**Цель:** Проверить, что при выборе платного тарифа создается платеж через YooKassa.

**Шаги:**
1. Войти в систему как владелец (owner)
2. Перейти на `/owner/tariff/change` или `/owner/tariffs`
3. Выбрать платный тариф (например, "Стандартный" с ценой > 0)
4. Нажать кнопку "Оплатить [цена] ₽"

**Ожидаемый результат:**
- [ ] Создается транзакция `BillingTransaction` со статусом `PROCESSING`
- [ ] Создается подписка `UserSubscription` со статусом `ACTIVE` (или `PENDING` до оплаты)
- [ ] В транзакции заполняется `external_id` (ID платежа YooKassa)
- [ ] Происходит редирект на страницу оплаты YooKassa
- [ ] URL платежа корректный (содержит `confirmation_url`)

**Проверка в БД:**
```sql
-- Проверить созданную транзакцию
SELECT id, user_id, subscription_id, status, amount, external_id, payment_method
FROM billing_transactions
WHERE user_id = [user_id]
ORDER BY created_at DESC
LIMIT 1;

-- Проверить подписку
SELECT id, user_id, tariff_plan_id, status, expires_at, payment_method
FROM user_subscriptions
WHERE user_id = [user_id]
ORDER BY created_at DESC
LIMIT 1;
```

---

### Сценарий 2: Оплата через YooKassa (тестовые карты)

**Цель:** Проверить процесс оплаты и обработку вебхуков.

**Шаги:**
1. Выполнить Сценарий 1 до редиректа на YooKassa
2. На странице оплаты YooKassa использовать тестовую карту:
   - **Успешная оплата:** `5555 5555 5555 4444` (любая дата в будущем, любой CVC)
   - **Отмена:** закрыть окно или нажать "Отмена"
3. После успешной оплаты вернуться на `/owner/subscription/payment_success`

**Ожидаемый результат:**
- [ ] Оплата проходит успешно через YooKassa
- [ ] YooKassa отправляет вебхук `payment.succeeded` на `/api/webhooks/yookassa`
- [ ] Вебхук обрабатывается корректно:
  - [ ] Проверка подлинности вебхука (если настроен `YOOKASSA_WEBHOOK_SECRET`)
  - [ ] Транзакция обновляется: статус → `COMPLETED`
  - [ ] Подписка продлевается: `expires_at` устанавливается корректно
  - [ ] `last_payment_at` обновляется
- [ ] На странице `/owner/subscription/payment_success` отображается успешное сообщение
- [ ] Редирект на `/owner/subscription` через 5 секунд работает

**Проверка в БД:**
```sql
-- Проверить статус транзакции после оплаты
SELECT id, status, processed_at, external_id, gateway_response
FROM billing_transactions
WHERE external_id = '[payment_id_from_yookassa]';

-- Проверить подписку после оплаты
SELECT id, status, expires_at, last_payment_at
FROM user_subscriptions
WHERE id = [subscription_id];
```

**Проверка логов:**
```bash
docker compose -f docker-compose.dev.yml logs web | grep -i "yookassa\|webhook\|payment"
docker compose -f docker-compose.dev.yml logs web | grep "process_payment_success"
```

---

### Сценарий 3: Отмена платежа

**Цель:** Проверить обработку отмененного платежа.

**Шаги:**
1. Выполнить Сценарий 1
2. На странице оплаты YooKassa нажать "Отмена" или закрыть окно
3. YooKassa отправляет вебхук `payment.canceled`

**Ожидаемый результат:**
- [ ] Вебхук `payment.canceled` обрабатывается
- [ ] Транзакция обновляется: статус → `CANCELLED`
- [ ] Подписка остается в исходном состоянии (или обновляется корректно)

**Проверка в БД:**
```sql
SELECT id, status, external_id
FROM billing_transactions
WHERE external_id = '[payment_id_from_yookassa]';
```

---

### Сценарий 4: Назначение подписки админом (платный тариф, оплачено)

**Цель:** Проверить назначение платной подписки админом с отметкой "Оплачено".

**Шаги:**
1. Войти в систему как суперадмин
2. Перейти на `/admin/subscriptions/assign`
3. Выбрать пользователя (владельца)
4. Выбрать платный тариф
5. **Отметить чекбокс "Оплачено"**
6. Нажать "Назначить подписку"

**Ожидаемый результат:**
- [ ] Чекбокс "Оплачено" показывается только для платных тарифов
- [ ] Создается подписка `UserSubscription` со статусом `ACTIVE`
- [ ] Создается транзакция `BillingTransaction` со статусом `COMPLETED`
- [ ] `external_id` = `admin_manual_{subscription_id}`
- [ ] `expires_at` устанавливается корректно (30 дней для monthly, 365 для yearly)
- [ ] `last_payment_at` заполняется

**Проверка в БД:**
```sql
SELECT bt.id, bt.status, bt.external_id, bt.amount,
       us.id, us.status, us.expires_at, us.last_payment_at
FROM billing_transactions bt
JOIN user_subscriptions us ON bt.subscription_id = us.id
WHERE us.user_id = [user_id]
ORDER BY bt.created_at DESC
LIMIT 1;
```

---

### Сценарий 5: Назначение подписки админом (платный тариф, НЕ оплачено)

**Цель:** Проверить назначение платной подписки админом БЕЗ отметки "Оплачено".

**Шаги:**
1. Войти в систему как суперадмин
2. Перейти на `/admin/subscriptions/assign`
3. Выбрать пользователя (владельца)
4. Выбрать платный тариф
5. **НЕ отмечать чекбокс "Оплачено"**
6. Нажать "Назначить подписку"

**Ожидаемый результат:**
- [ ] Создается подписка `UserSubscription` со статусом `PENDING` (или временный статус)
- [ ] Создается транзакция `BillingTransaction` со статусом `PENDING`
- [ ] `expires_at` НЕ устанавливается (или устанавливается `NULL`)
- [ ] Владелец видит требование оплаты

**Проверка в БД:**
```sql
SELECT bt.id, bt.status, bt.amount,
       us.id, us.status, us.expires_at
FROM billing_transactions bt
JOIN user_subscriptions us ON bt.subscription_id = us.id
WHERE us.user_id = [user_id]
ORDER BY bt.created_at DESC
LIMIT 1;
```

---

### Сценарий 6: Назначение подписки админом (бесплатный тариф)

**Цель:** Проверить назначение бесплатной подписки админом.

**Шаги:**
1. Войти в систему как суперадмин
2. Перейти на `/admin/subscriptions/assign`
3. Выбрать пользователя (владельца)
4. Выбрать бесплатный тариф (цена = 0)
5. Нажать "Назначить подписку"

**Ожидаемый результат:**
- [ ] Чекбокс "Оплачено" НЕ показывается для бесплатных тарифов
- [ ] Создается подписка `UserSubscription` со статусом `ACTIVE`
- [ ] Транзакция НЕ создается (или создается с суммой 0)
- [ ] `expires_at` устанавливается корректно

---

### Сценарий 7: Смена тарифа владельцем (бесплатный тариф)

**Цель:** Проверить смену на бесплатный тариф.

**Шаги:**
1. Войти в систему как владелец
2. Перейти на `/owner/tariff/change`
3. Выбрать бесплатный тариф
4. Нажать "Выбрать тариф"

**Ожидаемый результат:**
- [ ] Подписка создается напрямую, БЕЗ создания платежа
- [ ] Происходит редирект на `/owner/subscription` (или обновление страницы)
- [ ] Подписка активна, `expires_at` установлен

---

### Сценарий 8: История транзакций владельца

**Цель:** Проверить отображение истории платежей владельца.

**Шаги:**
1. Войти в систему как владелец
2. Перейти на `/owner/billing/transactions`
3. Проверить список транзакций

**Ожидаемый результат:**
- [ ] Отображаются все транзакции владельца
- [ ] Корректно отображаются: ID, дата, сумма, статус, тип
- [ ] Фильтр по статусу работает
- [ ] Кнопка "Детали" открывает модальное окно с полной информацией

**Проверка в БД:**
```sql
SELECT id, created_at, amount, currency, status, transaction_type, description
FROM billing_transactions
WHERE user_id = [user_id]
ORDER BY created_at DESC;
```

---

### Сценарий 9: Страница текущей подписки владельца

**Цель:** Проверить отображение информации о текущей подписке.

**Шаги:**
1. Войти в систему как владелец
2. Перейти на `/owner/subscription`

**Ожидаемый результат:**
- [ ] Отображается текущая подписка: тариф, срок действия, статус
- [ ] Отображаются лимиты использования и текущее использование
- [ ] Отображаются последние платежи (5 транзакций)
- [ ] Отображается настройка автопродления (если есть)
- [ ] Ссылки на "История платежей" и "Выбрать тариф" работают

---

### Сценарий 10: Автопродление подписки (Celery задачи)

**Цель:** Проверить автоматическое создание платежей для автопродления.

**Подготовка:**
1. Создать подписку владельцу с `auto_renewal=True`
2. Установить `expires_at` = текущая дата + 7 дней (для теста)
3. Проверить, что Celery worker и beat запущены:
   ```bash
   docker compose -f docker-compose.dev.yml ps celery_worker celery_beat
   ```

**Шаги:**
1. Запустить задачу вручную (для тестирования):
   ```bash
   docker compose -f docker-compose.dev.yml exec celery_worker celery -A core.celery.celery_app call check-expiring-subscriptions
   ```

**Ожидаемый результат:**
- [ ] Задача выполняется без ошибок
- [ ] Для подписок, истекающих через 7 дней:
  - [ ] Создается уведомление `SUBSCRIPTION_EXPIRING`
  - [ ] Если `auto_renewal=True` и тариф платный, создается транзакция и платеж через YooKassa
- [ ] Логи показывают созданные платежи и уведомления

**Проверка в БД:**
```sql
-- Проверить созданные транзакции для автопродления
SELECT bt.id, bt.status, bt.description, bt.external_id,
       us.id, us.auto_renewal, us.expires_at
FROM billing_transactions bt
JOIN user_subscriptions us ON bt.subscription_id = us.id
WHERE us.user_id = [user_id]
  AND bt.description LIKE '%Автоматическое продление%'
ORDER BY bt.created_at DESC;

-- Проверить созданные уведомления
SELECT id, type, status, title, message
FROM notifications
WHERE user_id = [user_id]
  AND type = 'subscription_expiring'
ORDER BY created_at DESC;
```

**Проверка логов:**
```bash
docker compose -f docker-compose.dev.yml logs celery_worker | grep -i "check-expiring\|auto.*renewal"
```

---

### Сценарий 11: Проверка истёкших подписок (Celery задачи)

**Цель:** Проверить автоматическое обновление статуса истёкших подписок.

**Подготовка:**
1. Создать подписку с `expires_at` = вчерашняя дата
2. Установить статус `ACTIVE`

**Шаги:**
1. Запустить задачу вручную:
   ```bash
   docker compose -f docker-compose.dev.yml exec celery_worker celery -A core.celery.celery_app call check-expired-subscriptions
   ```

**Ожидаемый результат:**
- [ ] Задача выполняется без ошибок
- [ ] Истёкшие подписки обновляются: статус → `EXPIRED`
- [ ] Создаются уведомления `SUBSCRIPTION_EXPIRED`

**Проверка в БД:**
```sql
SELECT id, status, expires_at
FROM user_subscriptions
WHERE expires_at < NOW()
  AND status = 'active';

-- После выполнения задачи:
SELECT id, status
FROM user_subscriptions
WHERE id = [subscription_id];
```

---

### Сценарий 12: Дашборд биллинга (админ)

**Цель:** Проверить отображение статистики в админ-панели.

**Шаги:**
1. Войти в систему как суперадмин
2. Перейти на `/admin/billing/`

**Ожидаемый результат:**
- [ ] Отображается статистика:
  - [ ] Общее количество транзакций
  - [ ] Общая выручка (сумма COMPLETED транзакций)
  - [ ] Количество активных подписок
  - [ ] Количество ожидающих платежей (PENDING)
- [ ] Отображаются последние транзакции (10 шт.)
- [ ] Все метрики заполнены реальными данными (не "-")

**Проверка в БД:**
```sql
-- Общее количество транзакций
SELECT COUNT(*) FROM billing_transactions;

-- Общая выручка
SELECT SUM(amount) FROM billing_transactions WHERE status = 'completed';

-- Активные подписки
SELECT COUNT(*) FROM user_subscriptions WHERE status = 'active';

-- Ожидающие платежи
SELECT COUNT(*) FROM billing_transactions WHERE status = 'pending';
```

---

### Сценарий 13: Обработка ошибок вебхуков

**Цель:** Проверить обработку некорректных вебхуков.

**Шаги:**
1. Отправить POST запрос на `/api/webhooks/yookassa` с некорректным телом:
   ```bash
   curl -X POST http://localhost:8001/api/webhooks/yookassa \
     -H "Content-Type: application/json" \
     -d '{"invalid": "data"}'
   ```

**Ожидаемый результат:**
- [ ] Запрос обрабатывается без ошибок 500
- [ ] Возвращается статус 200 OK (чтобы YooKassa не отправляла повторно)
- [ ] Ошибка логируется

**Проверка логов:**
```bash
docker compose -f docker-compose.dev.yml logs web | grep -i "webhook.*error\|yookassa.*error"
```

---

### Сценарий 14: Дубликаты вебхуков

**Цель:** Проверить защиту от обработки дубликатов.

**Шаги:**
1. Выполнить успешную оплату (Сценарий 2)
2. Дождаться обработки вебхука
3. Отправить тот же вебхук повторно (или через YooKassa повторно отправит)

**Ожидаемый результат:**
- [ ] Повторный вебхук игнорируется (если транзакция уже обработана)
- [ ] В логах сообщение: "Transaction already processed, ignoring webhook"

**Проверка в БД:**
```sql
-- Проверить, что транзакция не обновляется повторно
SELECT id, status, processed_at
FROM billing_transactions
WHERE external_id = '[payment_id]';

-- Проверить логи
```

---

## Проверка ошибок и краевых случаев

### Проверка 1: Тариф с нулевой ценой

- [ ] При выборе тарифа с `price=0` НЕ создается платеж через YooKassa
- [ ] Подписка создается напрямую

### Проверка 2: Отсутствие настроек YooKassa

- [ ] Если `YOOKASSA_SHOP_ID` или `YOOKASSA_SECRET_KEY` не заполнены, логируется предупреждение
- [ ] Попытка создать платеж возвращает ошибку с понятным сообщением

### Проверка 3: Недоступность API YooKassa

- [ ] При ошибке подключения к YooKassa логируется ошибка
- [ ] Транзакция помечается как `FAILED`
- [ ] Пользователю показывается понятное сообщение

### Проверка 4: Истекший срок транзакции

- [ ] Транзакция с `expires_at` в прошлом не используется для оплаты
- [ ] Создается новая транзакция

---

## Чеклист завершения тестирования

### Функциональность

- [ ] Все сценарии 1-14 выполнены успешно
- [ ] Все краевые случаи обработаны корректно
- [ ] Нет критических ошибок в логах

### База данных

- [ ] Все транзакции создаются с корректными данными
- [ ] Все подписки создаются и обновляются корректно
- [ ] Связи между таблицами корректны (foreign keys)

### Логирование

- [ ] Все важные события логируются
- [ ] Логи содержат достаточно информации для отладки
- [ ] Нет дублирования логов

### Безопасность

- [ ] Вебхуки проверяются на подлинность (если настроен секрет)
- [ ] Пользователи видят только свои транзакции
- [ ] Админ не может видеть платежные данные других пользователей (если не суперадмин)

---

## Известные проблемы и ограничения

1. **Тестовый режим YooKassa:**
   - В тестовом режиме платежи не списываются реально
   - Используются тестовые карты

2. **Вебхуки в локальной разработке:**
   - Для тестирования вебхуков нужен публичный URL (используйте ngrok или аналог)
   - Или тестировать вебхуки вручную через curl

3. **Время выполнения Celery задач:**
   - Задачи автопродления запускаются по расписанию
   - Для быстрого тестирования запускайте задачи вручную

---

## Дополнительные команды для отладки

### Проверка статуса платежа в YooKassa (вручную)

```python
from apps.web.services.payment_gateway.yookassa_service import YooKassaService

yookassa = YooKassaService()
status = await yookassa.get_payment_status("payment_id_from_yookassa")
print(status)
```

### Просмотр транзакций в БД

```bash
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "
SELECT 
    bt.id,
    bt.user_id,
    bt.status,
    bt.amount,
    bt.external_id,
    bt.created_at,
    us.tariff_plan_id
FROM billing_transactions bt
LEFT JOIN user_subscriptions us ON bt.subscription_id = us.id
ORDER BY bt.created_at DESC
LIMIT 10;
"
```

### Очистка тестовых данных (осторожно!)

```sql
-- Удалить тестовые транзакции (только для dev!)
DELETE FROM billing_transactions WHERE external_id LIKE 'admin_manual_%' OR external_id LIKE 'test_%';

-- Удалить тестовые подписки (только для dev!)
DELETE FROM user_subscriptions WHERE notes LIKE '%тест%' OR notes LIKE '%Test%';
```

---

## Контакты для поддержки

- **Документация YooKassa:** https://yookassa.ru/developers/api
- **Логи приложения:** `docker compose -f docker-compose.dev.yml logs web`
- **Логи Celery:** `docker compose -f docker-compose.dev.yml logs celery_worker celery_beat`

---

**Дата создания:** 31.10.2025  
**Версия:** 1.0  
**Статус:** Готово к тестированию

