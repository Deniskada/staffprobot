# Workflow: Проверка правок в apps/web/routes

**Триггер**: При изменении файлов в `apps/web/routes/**/*.py`  
**Режим**: StaffPro Architect  
**Описание**: Автоматическая проверка соблюдения правил роутинга

## Шаги workflow

### Шаг 1: Определение изменённых файлов
**JavaScript:**
```javascript
// Получить список изменённых файлов
const changedFiles = await getChangedFiles();
const routeFiles = changedFiles.filter(f => f.startsWith('apps/web/routes/'));
```

### Шаг 2: Проверка правил роутинга
**AI Query:**
```
Проверь изменённые файлы в apps/web/routes/ на соблюдение правил:

1. ПРЕФИКСЫ РОЛЕЙ:
   - Файлы в routes/owner/ должны иметь роуты без префикса /owner (префикс добавляется в app.py)
   - Файлы в routes/manager/ должны иметь роуты без префикса /manager
   - Файлы в routes/employee/ должны иметь роуты без префикса /employee
   - Проверь, что префикс указан ТОЛЬКО в apps/web/app.py через include_router

2. ДУБЛИРУЮЩИЕ РОУТЫ:
   - Проверь, что нет двух роутов с одинаковым методом (GET/POST) и путём
   - Используй grep для поиска дубликатов

3. ШАБЛОНЫ:
   - Должно использоваться: from apps.web.jinja import templates
   - НЕ должно быть: локальных Jinja2Templates

4. СЕССИИ БД:
   - Должно использоваться: Depends(get_db_session)
   - НЕ должно быть: async with get_async_session()

5. URLHelper:
   - Должно использоваться: URLHelper.get_web_url("/path")
   - НЕ должно быть: хардкода доменов типа "https://staffprobot.ru/..."

6. ЗАВИСИМОСТИ:
   - Проверь использование правильных зависимостей из apps.web.dependencies
   - require_owner_or_superadmin, require_manager_or_owner, get_current_user

Покажи список найденных нарушений с указанием файла и строки.
```

### Шаг 3: Предложение исправлений
**AI Query:**
```
Если найдены нарушения - предложи конкретные исправления с примерами кода.
Для каждого нарушения покажи:
- Текущий код (неправильный)
- Исправленный код (правильный)
- Объяснение почему это важно
```

### Шаг 4: Проверка линтера
**JavaScript:**
```javascript
const lints = await readLints(routeFiles);
if (lints.length > 0) {
    console.log("Ошибки линтера:", lints);
}
```

### Шаг 5: Предложение тестов
**AI Query:**
```
Предложи команды pytest для тестирования изменённых роутов:

1. Unit тесты для сервисов (если изменены services/)
2. Integration тесты для роутов
3. Команды для ручного тестирования через curl или веб-интерфейс

Примеры:
- docker compose -f docker-compose.dev.yml exec web pytest tests/integration/test_web_integration.py::test_route_name
- docker compose -f docker-compose.dev.yml exec web pytest tests/unit/test_service.py
```

## Использование

Workflow запускается автоматически при изменении файлов в `apps/web/routes/`.

Можно также запустить вручную:
1. Открыть Supercode UI
2. Выбрать workflow "Проверка правок в routes"
3. Указать файлы для проверки

## Результат

- Список нарушений правил (если есть)
- Предложения по исправлению
- Ошибки линтера
- Команды для тестирования
