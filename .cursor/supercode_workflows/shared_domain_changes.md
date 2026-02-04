# Workflow: Правки в shared/domain

**Триггер**: При изменении файлов в `shared/**/*.py` или `domain/**/*.py`  
**Режим**: StaffPro Architect  
**Описание**: Определение необходимых перезапусков контейнеров и тестов

## Шаги workflow

### Шаг 1: Определение изменённых файлов
**JavaScript:**
```javascript
const changedFiles = await getChangedFiles();
const sharedFiles = changedFiles.filter(f => f.startsWith('shared/'));
const domainFiles = changedFiles.filter(f => f.startsWith('domain/'));
```

### Шаг 2: Определение затронутых контейнеров
**AI Query:**
```
Определи, какие контейнеры Docker нужно перезапустить на основе изменённых файлов:

ПРАВИЛА:
- apps/web/* → restart web
- apps/bot/* → restart bot
- core/celery/tasks/* → restart celery_worker celery_beat
- shared/* или domain/* → restart web bot celery_worker celery_beat

Изменённые файлы:
{changedFiles}

Покажи список контейнеров для перезапуска и команду:
docker compose -f docker-compose.dev.yml restart <контейнеры>
```

### Шаг 3: Предложение команды перезапуска
**JavaScript:**
```javascript
// Предложить команду перезапуска
const containers = ['web', 'bot', 'celery_worker', 'celery_beat'];
const command = `docker compose -f docker-compose.dev.yml restart ${containers.join(' ')}`;
console.log(`Команда перезапуска: ${command}`);
```

### Шаг 4: Анализ изменений
**AI Query:**
```
Проанализируй изменения в shared/ или domain/:
1. Какие сущности/сервисы изменены?
2. Какие зависимости могут быть затронуты?
3. Какие части системы могут сломаться?

Покажи список потенциально затронутых компонентов:
- Веб-роуты (apps/web/routes/)
- Бот-обработчики (apps/bot/handlers/)
- Celery задачи (core/celery/tasks/)
- Другие сервисы
```

### Шаг 5: Предложение тестов
**AI Query:**
```
Предложи интеграционные тесты для проверки изменений:

1. Тесты для изменённых сущностей/сервисов
2. Тесты для зависимых компонентов
3. Команды для запуска тестов

Примеры:
- docker compose -f docker-compose.dev.yml exec web pytest tests/integration/test_entity.py
- docker compose -f docker-compose.dev.yml exec web pytest tests/unit/test_service.py::test_method

Также предложи команды для проверки логов после перезапуска:
- docker compose -f docker-compose.dev.yml logs web --tail 50
- docker compose -f docker-compose.dev.yml logs bot --tail 50
```

### Шаг 6: Проверка кэша
**AI Query:**
```
Если изменены shared/ или domain/, может потребоваться очистка кэша Redis.

Предложи команды:
1. Проверка кэша: docker compose -f docker-compose.dev.yml exec redis redis-cli KEYS "*"
2. Очистка кэша (если нужно): docker compose -f docker-compose.dev.yml exec redis redis-cli FLUSHDB

Также проверь, не используются ли изменённые сущности в кэшированных запросах.
```

## Использование

Workflow запускается автоматически при изменении файлов в `shared/` или `domain/`.

Можно также запустить вручную:
1. Открыть Supercode UI
2. Выбрать workflow "Правки в shared/domain"
3. Указать файлы для анализа

## Результат

- Список контейнеров для перезапуска
- Команда перезапуска
- Список потенциально затронутых компонентов
- Команды для тестирования
- Команды для проверки логов
- Рекомендации по очистке кэша

## Важные замечания

⚠️ **Внимание**: Изменения в `shared/` или `domain/` затрагивают ВСЕ компоненты системы (web, bot, celery). Обязательно:
1. Перезапустить все затронутые контейнеры
2. Проверить логи на ошибки
3. Запустить интеграционные тесты
4. Проверить работу в реальных условиях
