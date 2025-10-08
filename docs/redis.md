# Использование Redis в StaffProBot

## Обзор

Redis используется в проекте StaffProBot для двух основных целей:
1. **Кэширование данных** — ускорение доступа к часто запрашиваемым данным
2. **Celery backend** — хранение результатов фоновых задач

### Архитектура

- **Клиент**: `redis.asyncio` (асинхронный Python-клиент)
- **Конфигурация**: `core/config/settings.py`
  - URL: `redis://localhost:6379` (по умолчанию)
  - DB: `0` (база данных Redis)
- **Подключение**: Глобальный экземпляр `cache` в `core/cache/redis_cache.py`
- **Graceful degradation**: При недоступности Redis приложение продолжает работать с warnings в логах

---

## Текущие сценарии использования

### 1. Кэширование через CacheService

**Файл**: `core/cache/cache_service.py`

Определены методы для кэширования:

#### Пользователи
- **Ключ**: `user:{user_id}`
- **TTL**: 15 минут
- **Методы**: `get_user()`, `set_user()`, `delete_user()`

#### Объекты
- **Ключ**: `object:{object_id}`
- **TTL**: 15 минут
- **Методы**: `get_object()`, `set_object()`, `delete_object()`

#### Смены
- **Ключ**: `shift:{shift_id}`
- **TTL**: 5 минут
- **Методы**: `get_shift()`, `set_shift()`, `delete_shift()`

#### Активные смены пользователя
- **Ключ**: `active_shifts:{user_id}`
- **TTL**: 5 минут
- **Методы**: `get_user_active_shifts()`, `set_user_active_shifts()`, `delete_user_active_shifts()`

#### Объекты пользователя
- **Ключ**: `user_objects:{user_id}`
- **TTL**: 15 минут
- **Методы**: `get_user_objects()`, `set_user_objects()`, `delete_user_objects()`

#### Аналитика
- **Ключ**: `analytics:{cache_key}`
- **TTL**: 1 час
- **Методы**: `get_analytics_data()`, `set_analytics_data()`

### 2. PIN-коды для веб-аутентификации

**Файл**: `apps/web/services/auth_service.py`

- **Ключ**: `pin:{telegram_id}`
- **TTL**: 5 минут (300 секунд)
- **Тип**: Одноразовый (удаляется после успешной проверки)
- **Применение**: 
  - Генерация при запросе `/auth/send-pin`
  - Проверка при `/auth/login`
  - Для тестовых пользователей (`is_test_user=true`) пропускается отправка, принимается любой 6-значный PIN

### 3. Системные настройки

**Файл**: `apps/web/services/system_settings_service.py`

- **Префикс**: `system_settings:`
- **TTL**: 1 час (3600 секунд)
- **Кэшируемые настройки**:
  - `domain` — основной домен системы
  - `use_https` — использование HTTPS
  - `ssl_email` — email для Let's Encrypt
  - `enable_test_users` — режим тестовых пользователей
  - Другие системные параметры

### 4. SSL-мониторинг

**Файл**: `apps/web/services/ssl_monitoring_service.py`

- **Применение**: Кэширование статуса SSL-сертификатов
- **TTL**: 1 час
- **Цель**: Уменьшение нагрузки при проверке состояния сертификатов

### 5. Celery backend

**Файл**: `core/celery/celery_app.py`

- **Broker**: RabbitMQ (`settings.rabbitmq_url`)
- **Backend**: Redis (`settings.redis_url`)
- **Применение**: Хранение результатов асинхронных задач
- **TTL результатов**: 1 час (`result_expires=3600`)
- **Сериализация**: JSON

#### Очереди задач:
- `notifications` — уведомления
- `shifts` — смены
- `analytics` — аналитика

---

## Celery периодические задачи

Используют Redis как backend для хранения результатов:

### 1. process-reminders
- **Расписание**: каждые 30 минут
- **Файл**: `core/celery/tasks/notification_tasks.py`
- **Назначение**: Обработка напоминаний о предстоящих сменах

### 2. auto-close-shifts
- **Расписание**: каждые 30 минут
- **Файл**: `core/celery/tasks/shift_tasks.py`
- **Назначение**: Автоматическое закрытие просроченных смен

### 3. cleanup-cache
- **Расписание**: каждые 6 часов
- **Файл**: `core/celery/tasks/analytics_tasks.py`
- **Назначение**: Очистка устаревших кэшей аналитики

### 4. plan-next-year-timeslots
- **Расписание**: 1 декабря в 03:00
- **Файл**: `core/celery/tasks/shift_tasks.py`
- **Назначение**: Планирование тайм-слотов на следующий год

---

## Проблемы и ограничения

### ⚠️ Критические проблемы

#### 1. CacheService не используется в бизнес-логике
**Проблема**: CacheService создан с полным набором методов, но сервисы (`ContractService`, `ObjectService`, `ShiftService`) обращаются к БД напрямую без кэширования.

**Влияние**: 
- Каждый запрос к списку сотрудников выполняет несколько SQL-запросов
- Повторные запросы к одним и тем же данным не оптимизированы
- Высокая нагрузка на PostgreSQL

**Где не используется**:
- `apps/web/services/contract_service.py` — методы `get_contract_employees_by_telegram_id()`, `get_owner_objects()`
- `apps/web/services/object_service.py` — методы получения списков объектов
- `shared/services/manager_permission_service.py` — `get_user_accessible_objects()`

#### 2. Нет автоматической инвалидации кэша
**Проблема**: При изменении данных в БД (создание договора, обновление объекта) кэш не инвалидируется.

**Влияние**: Если добавить кэширование без инвалидации, пользователи будут видеть устаревшие данные.

**Решение**: Добавить вызовы `CacheService.invalidate_*()` после операций изменения данных.

#### 3. Декоратор @cached не применяется
**Проблема**: В `core/cache/redis_cache.py` определен универсальный декоратор `@cached`, но он не используется ни в одном сервисе.

**Потенциал**: Простое добавление декоратора к методам сервисов автоматически добавит кэширование.

### ⚠️ Средние проблемы

#### 4. Нет мониторинга производительности кэша
**Проблема**: Нет визуализации hit rate, memory usage, evicted keys.

**Влияние**: Невозможно оценить эффективность кэширования и выявить проблемы.

**Решение**: 
- Endpoint `/admin/cache/stats` для просмотра статистики
- Интеграция с Prometheus/Grafana

#### 5. Отсутствие ограничений памяти
**Проблема**: Redis не имеет ограничений по памяти и политики вытеснения.

**Влияние**: При утечках или избыточном кэшировании Redis может занять всю доступную память.

**Решение**: Настроить `maxmemory` и `maxmemory-policy` в docker-compose.

#### 6. Нет rate limiting
**Проблема**: API не защищен от злоупотреблений и DDoS.

**Влияние**: Потенциальная перегрузка системы при массовых запросах.

**Решение**: Использовать Redis для подсчета запросов в единицу времени.

---

## Рекомендации по улучшению

### Приоритет 1 — Критические улучшения

#### 1. Применить кэширование в сервисах

**Файлы для изменения**:
- `apps/web/services/contract_service.py`
- `apps/web/services/object_service.py`
- `shared/services/manager_permission_service.py`

**Пример 1: Декоратор для метода**
```python
# apps/web/services/contract_service.py
from core.cache.cache_service import cached
from datetime import timedelta

class ContractService:
    @cached(ttl=timedelta(minutes=15), key_prefix="contract_employees")
    async def get_contract_employees_by_telegram_id(self, telegram_id: int):
        # Существующая логика запроса к БД
        # ...
```

**Пример 2: Явное использование CacheService**
```python
from core.cache.cache_service import CacheService

async def get_owner_objects(self, owner_telegram_id: int):
    # Проверяем кэш
    cached = await CacheService.get_user_objects(owner_telegram_id)
    if cached:
        return cached
    
    # Запрос к БД
    objects = await self._fetch_objects_from_db(owner_telegram_id)
    
    # Сохраняем в кэш
    await CacheService.set_user_objects(owner_telegram_id, objects)
    
    return objects
```

#### 2. Автоматическая инвалидация кэша

**Где добавить**:

```python
# apps/web/services/contract_service.py
async def create_contract(self, contract_data: dict):
    contract = Contract(**contract_data)
    self.session.add(contract)
    await self.session.commit()
    
    # ✅ Инвалидация кэша
    await CacheService.invalidate_user_cache(contract.employee_id)
    await CacheService.invalidate_user_cache(contract.owner_id)
    await CacheService.delete_user_objects(contract.owner_id)
    
    return contract

async def update_object(self, object_id: int, data: dict):
    # ...обновление объекта...
    await self.session.commit()
    
    # ✅ Инвалидация кэша
    await CacheService.invalidate_object_cache(object_id)
```

#### 3. Мониторинг кэша

**Endpoint для админки**:
```python
# apps/web/routes/admin.py
@router.get("/cache/stats")
async def admin_cache_stats(current_user: dict = Depends(require_superadmin)):
    """Статистика Redis кэша"""
    stats = await CacheService.get_cache_stats()
    return {
        "redis": stats.get("redis_stats", {}),
        "keys": stats.get("key_counts", {}),
        "recommendations": []
    }
```

**UI в админке** (`apps/web/templates/admin/monitoring.html`):
- Hit rate: `{hits / (hits + misses) * 100}%`
- Memory usage: `used_memory_human`
- Количество ключей по типам
- Кнопка "Очистить кэш"

---

### Приоритет 2 — Оптимизации

#### 4. Кэширование календарных данных

**Файлы**: 
- `apps/web/services/object_service.py` (метод `get_timeslots_by_object`)
- `shared/services/calendar_filter_service.py`

**Пример**:
```python
async def get_timeslots_by_object(self, object_id: int, date_from, date_to, ...):
    cache_key = f"timeslots:{object_id}:{date_from}:{date_to}"
    cached = await CacheService.get(cache_key)
    if cached:
        return cached
    
    # Запрос к БД
    timeslots = await self._fetch_timeslots(...)
    
    # Кэш на 10 минут
    await CacheService.set(cache_key, timeslots, ttl=timedelta(minutes=10))
    return timeslots
```

**Инвалидация**: При создании/удалении тайм-слота:
```python
await CacheService.delete(f"timeslots:{object_id}:*")  # pattern-based deletion
```

#### 5. Rate limiting через Redis

**Новый сервис**: `core/utils/rate_limiter.py`

```python
class RateLimiter:
    @staticmethod
    async def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
        """Проверка лимита запросов"""
        from core.cache.redis_cache import cache
        
        current = await cache.redis.incr(key)
        if current == 1:
            await cache.redis.expire(key, window_seconds)
        
        return current <= max_requests

# Применение в middleware:
# if not await RateLimiter.check_rate_limit(f"rate:{ip}", 100, 60):
#     raise HTTPException(status_code=429, detail="Too many requests")
```

#### 6. Конфигурация Redis с ограничениями памяти

**Файл**: `docker-compose.dev.yml` и `docker-compose.prod.yml`

```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --save 900 1
    --save 300 10
    --appendonly yes
  volumes:
    - redis_data:/data
```

**Политики вытеснения**:
- `allkeys-lru` — удаляет наименее используемые ключи
- `volatile-lru` — удаляет только ключи с TTL
- `allkeys-random` — случайное удаление

---

### Приоритет 3 — Расширенные возможности

#### 7. Pub/Sub для реал-тайм обновлений

**Применение**: WebSocket уведомления о новых сменах, изменениях расписания.

**Пример**:
```python
# Publisher (при создании смены)
await cache.redis.publish("shifts:updates", json.dumps({
    "type": "shift_created",
    "shift_id": shift.id,
    "user_id": shift.user_id
}))

# Subscriber (WebSocket сервер)
pubsub = cache.redis.pubsub()
await pubsub.subscribe("shifts:updates")
async for message in pubsub.listen():
    # Отправка через WebSocket клиентам
    await websocket.send_json(message)
```

#### 8. Геопространственные запросы (Redis Geo)

**Команды**:
- `GEOADD objects:locations {lon} {lat} {object_id}`
- `GEORADIUS objects:locations {lon} {lat} 5 km`

**Применение**: Быстрый поиск ближайших объектов (альтернатива PostGIS для некритичных случаев).

**Ограничение**: PostGIS остается primary решением, Redis Geo — для кэширования часто запрашиваемых координат.

#### 9. Distributed locks

**Библиотека**: `redis.lock`

**Применение**: Предотвращение race conditions при одновременном планировании смен.

```python
from redis import asyncio as aioredis

async def plan_shift_with_lock(object_id: int, slot_id: int):
    lock_key = f"lock:plan_shift:{object_id}:{slot_id}"
    async with cache.redis.lock(lock_key, timeout=10):
        # Критическая секция: проверка и создание смены
        existing = await check_existing_shift(...)
        if not existing:
            await create_shift(...)
```

---

## Статистика и мониторинг

### Доступные метрики Redis

Через `await cache.get_stats()`:
- `connected_clients` — количество подключенных клиентов
- `used_memory` — использованная память (байты)
- `used_memory_human` — использованная память (читаемый формат)
- `total_commands_processed` — общее количество команд
- `keyspace_hits` — попадания в кэш
- `keyspace_misses` — промахи кэша
- `hit_rate` — процент попаданий

### Рекомендуемые дашборды

**Grafana панели**:
1. Hit Rate (%) — тренд попаданий в кэш
2. Memory Usage (MB) — использование памяти
3. Key Counts — количество ключей по типам
4. Evicted Keys — вытесненные ключи (при переполнении)
5. Commands/sec — нагрузка на Redis

**Prometheus метрики** (через `redis_exporter`):
- `redis_connected_clients`
- `redis_memory_used_bytes`
- `redis_keyspace_hits_total`
- `redis_keyspace_misses_total`
- `redis_evicted_keys_total`

---

## Конфигурация для production

### docker-compose.prod.yml

```yaml
redis:
  image: redis:7-alpine
  container_name: staffprobot-redis-prod
  restart: always
  command: >
    redis-server
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --save 900 1
    --save 300 10
    --save 60 10000
    --appendonly yes
    --requirepass ${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
  networks:
    - staffprobot-network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 3
```

### Переменные окружения (.env)

```env
REDIS_URL=redis://localhost:6379
REDIS_DB=0
REDIS_PASSWORD=your-secure-password-here
```

---

## Примеры кода для улучшений

### Пример 1: Кэширование списка сотрудников

**До**:
```python
# apps/web/services/contract_service.py
async def get_contract_employees_by_telegram_id(self, telegram_id: int):
    # Прямой запрос к БД каждый раз
    async with get_async_session() as session:
        result = await session.execute(query)
        return result.scalars().all()
```

**После**:
```python
from core.cache.cache_service import cached
from datetime import timedelta

@cached(ttl=timedelta(minutes=15), key_prefix="contract_employees")
async def get_contract_employees_by_telegram_id(self, telegram_id: int):
    # Запрос выполнится только при cache miss
    async with get_async_session() as session:
        result = await session.execute(query)
        return result.scalars().all()
```

### Пример 2: Инвалидация при создании договора

```python
# apps/web/services/contract_service.py
from core.cache.cache_service import CacheService

async def create_contract(self, contract_data: dict):
    contract = Contract(**contract_data)
    self.session.add(contract)
    await self.session.commit()
    await self.session.refresh(contract)
    
    # ✅ Инвалидация кэша сотрудника и владельца
    await CacheService.invalidate_user_cache(contract.employee_id)
    await CacheService.invalidate_user_cache(contract.owner_id)
    
    # ✅ Инвалидация списков объектов
    await CacheService.delete_user_objects(contract.owner_id)
    
    return contract
```

### Пример 3: Endpoint для статистики кэша

```python
# apps/web/routes/admin.py
@router.get("/cache/stats", response_class=HTMLResponse)
async def admin_cache_stats(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Статистика Redis кэша"""
    from core.cache.cache_service import CacheService
    
    stats = await CacheService.get_cache_stats()
    
    return templates.TemplateResponse("admin/cache_stats.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats
    })
```

### Пример 4: Rate limiting middleware

```python
# core/middleware/rate_limit.py
from fastapi import Request, HTTPException
from core.cache.redis_cache import cache

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    # Счетчик запросов
    count = await cache.redis.incr(key)
    
    if count == 1:
        # Первый запрос — устанавливаем TTL 1 минута
        await cache.redis.expire(key, 60)
    
    if count > 100:  # Макс 100 запросов/минуту
        raise HTTPException(status_code=429, detail="Too many requests")
    
    response = await call_next(request)
    return response
```

---

## Чек-лист внедрения улучшений

### Фаза 1: Базовое кэширование (1-2 дня)
- [ ] Добавить `@cached` декоратор к методам `ContractService`
- [ ] Добавить `@cached` декоратор к методам `ObjectService`
- [ ] Добавить инвалидацию в `create_contract()`, `update_contract()`, `terminate_contract()`
- [ ] Добавить инвалидацию в `create_object()`, `update_object()`, `delete_object()`
- [ ] Протестировать на dev: создать договор → проверить инвалидацию кэша

### Фаза 2: Мониторинг (1 день)
- [ ] Создать endpoint `/admin/cache/stats`
- [ ] Создать UI страницу `admin/cache_stats.html`
- [ ] Добавить Prometheus метрики через `redis_exporter`
- [ ] Создать Grafana dashboard для Redis

### Фаза 3: Оптимизация конфигурации (0.5 дня)
- [ ] Настроить `maxmemory` и `maxmemory-policy` в `docker-compose.*.yml`
- [ ] Добавить `REDIS_PASSWORD` в `.env`
- [ ] Обновить healthcheck для Redis

### Фаза 4: Rate limiting (1 день)
- [ ] Создать `RateLimiter` утилиту
- [ ] Добавить middleware для API endpoints
- [ ] Настроить лимиты по ролям (owner: 200/мин, employee: 100/мин)

### Фаза 5: Расширенные возможности (2-3 дня, опционально)
- [ ] Redis Pub/Sub для WebSocket уведомлений
- [ ] Distributed locks для критических операций
- [ ] Redis Geo для кэширования координат

---

## Команды для диагностики

### Подключение к Redis (dev)
```bash
docker compose -f docker-compose.dev.yml exec redis redis-cli
```

### Просмотр всех ключей
```bash
redis-cli KEYS "*"
```

### Статистика Redis
```bash
redis-cli INFO stats
```

### Очистка всех ключей (ОСТОРОЖНО!)
```bash
redis-cli FLUSHDB
```

### Мониторинг в реальном времени
```bash
redis-cli MONITOR
```

---

## Итоги

### Что работает хорошо
✅ Redis подключен и стабильно работает  
✅ PIN-коды для аутентификации эффективно используют кэш  
✅ Системные настройки кэшируются корректно  
✅ Celery backend работает через Redis  
✅ Graceful degradation при отключении Redis  

### Что нужно улучшить
❌ CacheService создан, но не используется в бизнес-логике  
❌ Нет автоматической инвалидации кэша  
❌ Отсутствует мониторинг производительности  
❌ Нет ограничений памяти и политики вытеснения  
❌ Отсутствует rate limiting  

### Потенциальный эффект от улучшений
- **Производительность**: Снижение нагрузки на PostgreSQL на 40-60%
- **Скорость отклика**: Уменьшение времени ответа API на 30-50% для повторных запросов
- **Масштабируемость**: Поддержка большего количества одновременных пользователей
- **Стабильность**: Защита от перегрузок через rate limiting

---

**Автор документа**: AI Assistant  
**Дата создания**: 08.10.2025  
**Версия проекта**: StaffProBot v0.1.0

