# План тестирования: Redis кэширование Фаза 1

## Цель
Проверить корректность работы кэширования и инвалидации в ContractService и ObjectService после добавления декораторов @cached.

## Окружение
- **Среда**: Development (docker-compose.dev.yml)
- **База данных**: staffprobot_dev
- **Redis**: redis://localhost:6379 (контейнер staffprobot_redis_dev)
- **Интерфейс**: http://localhost:8001

---

## Тест 1: Кэширование списка сотрудников (ContractService)

### Предусловия
- Залогинен как владелец
- Есть минимум 1 активный договор с сотрудником

### Шаги тестирования

#### 1.1. Проверка базового кэширования

```bash
# Очистить Redis перед тестом
docker compose -f docker-compose.dev.yml exec redis redis-cli FLUSHDB

# Открыть страницу списка сотрудников
# http://localhost:8001/owner/employees
```

**Ожидаемый результат:**
- Страница загружается успешно
- Сотрудники отображаются корректно
- В логах web: `Cache miss for key: contract_employees:...`

#### 1.2. Повторный запрос (проверка кэша)

```bash
# Обновить страницу F5
# http://localhost:8001/owner/employees
```

**Ожидаемый результат:**
- Страница загружается быстрее (из кэша)
- Данные те же
- В логах web: `Cache hit for key: contract_employees:...`

#### 1.3. Проверка ключа в Redis

```bash
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "contract_employees:*"
docker compose -f docker-compose.dev.yml exec redis redis-cli TTL "contract_employees:..."
```

**Ожидаемый результат:**
- Ключ существует
- TTL примерно 900 секунд (15 минут)

#### 1.4. Инвалидация при создании договора

```bash
# Создать новый договор через UI
# http://localhost:8001/owner/employees/create

# После создания проверить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "contract_employees:*"
```

**Ожидаемый результат:**
- Ключ `contract_employees:*` удален из Redis
- Следующий запрос к `/owner/employees` создаст новый кэш

#### 1.5. Инвалидация при обновлении договора

```bash
# Открыть страницу сотрудников (создаст кэш)
# http://localhost:8001/owner/employees

# Обновить любой договор
# http://localhost:8001/owner/employees/contract/X/edit

# Проверить Redis после обновления
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "contract_employees:*"
```

**Ожидаемый результат:**
- Кэш инвалидирован после update_contract()

#### 1.6. Инвалидация при расторжении

```bash
# Создать кэш
# Расторгнуть договор через UI

# Проверить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "contract_employees:*"
```

**Ожидаемый результат:**
- Кэш инвалидирован после terminate_contract()

---

## Тест 2: Кэширование объектов владельца (ObjectService)

### Предусловия
- Залогинен как владелец
- Есть минимум 1 объект

### Шаги тестирования

#### 2.1. Проверка базового кэширования

```bash
# Очистить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli FLUSHDB

# Открыть страницу объектов
# http://localhost:8001/owner/objects
```

**Ожидаемый результат:**
- Объекты загружаются
- В логах: `Cache miss for key: objects_by_owner:...`

#### 2.2. Повторный запрос

```bash
# Обновить страницу
# http://localhost:8001/owner/objects
```

**Ожидаемый результат:**
- В логах: `Cache hit for key: objects_by_owner:...`
- Данные из кэша

#### 2.3. Проверка TTL

```bash
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "objects_by_owner:*"
docker compose -f docker-compose.dev.yml exec redis redis-cli TTL "objects_by_owner:..."
```

**Ожидаемый результат:**
- TTL ≈ 900 секунд

#### 2.4. Инвалидация при создании объекта

```bash
# Создать кэш (открыть /owner/objects)
# Создать новый объект
# http://localhost:8001/owner/objects/create

# Проверить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "objects_by_owner:*"
```

**Ожидаемый результат:**
- Кэш владельца инвалидирован
- Кэш нового объекта `object:X` также инвалидирован

#### 2.5. Инвалидация при обновлении

```bash
# Создать кэш
# Обновить объект через UI
# http://localhost:8001/owner/objects/X/edit

# Проверить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "object:*"
```

**Ожидаемый результат:**
- `object:X` удален из Redis

#### 2.6. Инвалидация при удалении

```bash
# Удалить объект (мягкое удаление)
# Проверить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "object:*"
```

**Ожидаемый результат:**
- Кэш объекта инвалидирован

---

## Тест 3: Управляющий (Manager) - обновление объекта

### Предусловия
- Залогинен как управляющий
- Есть доступ к объектам владельца

### Шаги

#### 3.1. Обновление объекта управляющим

```bash
# Открыть объект для редактирования
# http://localhost:8001/manager/objects/X/edit

# Обновить данные (например, часовая ставка)
# Сохранить

# Проверить инвалидацию
docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "object:*"
```

**Ожидаемый результат:**
- Метод `update_object_by_manager()` вызвал `invalidate_object_cache()`
- Кэш объекта удален

---

## Тест 4: Проверка логов

### Команды

```bash
# Смотреть логи web в реальном времени
docker compose -f docker-compose.dev.yml logs -f web | grep -i "cache"

# Искать упоминания о кэше
docker compose -f docker-compose.dev.yml logs web | grep "Cache hit"
docker compose -f docker-compose.dev.yml logs web | grep "Cache miss"
docker compose -f docker-compose.dev.yml logs web | grep "invalidate"
```

**Ожидаемый результат:**
- При первом запросе: "Cache miss"
- При повторном: "Cache hit"
- При создании/обновлении: "invalidate_user_cache" или "invalidate_object_cache"

---

## Тест 5: Проверка производительности (базовая)

### Инструмент: Browser DevTools

```bash
# Открыть DevTools -> Network
# Очистить Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli FLUSHDB

# Загрузить /owner/employees - записать время (T1)
# Обновить страницу - записать время (T2)
```

**Ожидаемый результат:**
- T2 < T1 (страница из кэша загружается быстрее)
- Разница минимум 20-30% для списков с >10 сотрудников

---

## Тест 6: Graceful degradation (Redis недоступен)

### Шаги

```bash
# Остановить Redis
docker compose -f docker-compose.dev.yml stop redis

# Открыть /owner/employees
# http://localhost:8001/owner/employees
```

**Ожидаемый результат:**
- Страница загружается (без ошибок)
- В логах: `Redis not connected, skipping cache`
- Данные берутся из БД напрямую

```bash
# Запустить Redis обратно
docker compose -f docker-compose.dev.yml start redis
```

---

## Тест 7: Мониторинг Redis

### Команды

```bash
# Общая статистика Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli INFO stats

# Количество ключей
docker compose -f docker-compose.dev.yml exec redis redis-cli DBSIZE

# Hit rate
docker compose -f docker-compose.dev.yml exec redis redis-cli INFO stats | grep keyspace
```

**Ожидаемый результат:**
- `keyspace_hits` растет при повторных запросах
- `keyspace_misses` растет при первых запросах
- Hit rate = hits / (hits + misses) > 0.5 после нескольких циклов

---

## Чек-лист финальной проверки

- [ ] ContractService.get_contract_employees_by_telegram_id() кэширует на 15 мин
- [ ] ContractService.get_all_contract_employees_by_telegram_id() кэширует на 15 мин
- [ ] ContractService.get_owner_objects() кэширует на 15 мин
- [ ] ObjectService.get_objects_by_owner() кэширует на 15 мин
- [ ] create_contract() инвалидирует кэш employee и owner
- [ ] update_contract() инвалидирует кэш employee и owner
- [ ] terminate_contract() инвалидирует кэш employee и owner
- [ ] create_object() инвалидирует кэш объекта
- [ ] update_object() инвалидирует кэш объекта
- [ ] update_object_by_manager() инвалидирует кэш объекта
- [ ] delete_object() инвалидирует кэш объекта
- [ ] Redis работает корректно в dev окружении
- [ ] Graceful degradation работает при недоступности Redis
- [ ] Логи показывают cache hit/miss
- [ ] Производительность улучшилась (визуально)

---

## Инструменты для диагностики

### 1. Redis CLI внутри контейнера

```bash
docker compose -f docker-compose.dev.yml exec redis redis-cli

# Команды внутри:
KEYS *                    # Все ключи
KEYS contract_*          # Ключи договоров
KEYS object:*            # Ключи объектов
TTL key_name             # Время жизни ключа
GET key_name             # Значение ключа
FLUSHDB                  # Очистить БД (осторожно!)
MONITOR                  # Реал-тайм мониторинг команд
```

### 2. Просмотр логов

```bash
# Все логи web
docker compose -f docker-compose.dev.yml logs web

# Только кэш
docker compose -f docker-compose.dev.yml logs web | grep -i cache

# Следить в реальном времени
docker compose -f docker-compose.dev.yml logs -f web
```

### 3. Проверка статуса Redis

```bash
docker compose -f docker-compose.dev.yml ps redis
docker compose -f docker-compose.dev.yml exec redis redis-cli PING
```

---

## Отчет о тестировании (заполнить после)

| Тест | Статус | Примечания |
|------|--------|------------|
| 1.1 Базовое кэширование сотрудников | ⬜ | |
| 1.2 Cache hit при повторном запросе | ⬜ | |
| 1.3 TTL = 15 минут | ⬜ | |
| 1.4 Инвалидация при create_contract | ⬜ | |
| 1.5 Инвалидация при update_contract | ⬜ | |
| 1.6 Инвалидация при terminate_contract | ⬜ | |
| 2.1 Базовое кэширование объектов | ⬜ | |
| 2.2 Cache hit при повторе | ⬜ | |
| 2.3 TTL = 15 минут | ⬜ | |
| 2.4 Инвалидация при create_object | ⬜ | |
| 2.5 Инвалидация при update_object | ⬜ | |
| 2.6 Инвалидация при delete_object | ⬜ | |
| 3.1 Инвалидация update_object_by_manager | ⬜ | |
| 4 Логи cache hit/miss | ⬜ | |
| 5 Производительность улучшилась | ⬜ | |
| 6 Graceful degradation | ⬜ | |
| 7 Мониторинг Redis | ⬜ | |

**Легенда:** ✅ Пройден | ❌ Провален | ⬜ Не проверен

---

## Следующие шаги после тестирования

Если все тесты пройдены:
1. Зафиксировать изменения: `git push origin feature/iteration-21-redis-optimization`
2. Создать Pull Request в main
3. Приступить к Фазе 2: Мониторинг кэша

Если есть проблемы:
1. Зафиксировать найденные баги
2. Исправить перед переходом к следующей фазе
3. Повторить тестирование

