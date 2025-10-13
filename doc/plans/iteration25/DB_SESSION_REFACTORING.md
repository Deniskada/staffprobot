# 🔧 Рефакторинг паттерна работы с БД в веб-роутах

## 📊 Масштаб проблемы

**Найдено:** 183 использования `async with get_async_session()` в 19 файлах роутов  
**Исправлено:** 23 использования в `apps/web/routes/admin_notifications.py` (Iteration 25)  
**Осталось исправить:** 160 использований в 18 файлах

---

## 🔴 Критичность проблемы

### Последствия при текущем подходе:

1. **Утечка соединений к БД**
   - Каждый запрос создает новое соединение
   - Connection pool исчерпывается при ~50 одновременных пользователях
   - Ошибки "Too many connections" при нагрузке

2. **Проблемы с производительностью**
   - Создание/закрытие соединений медленнее переиспользования пула
   - Деградация при масштабировании
   - Невозможность эффективного кэширования соединений

3. **Нарушение архитектуры FastAPI**
   - Dependency Injection игнорируется
   - Нет автоматической очистки ресурсов
   - Сложная обработка ошибок и откат транзакций

4. **Транзакционная целостность**
   - Нет единого контекста транзакции для всего запроса
   - Невозможность использовать несколько сервисов в одной транзакции
   - Отсутствие автоматического rollback при ошибках

---

## ✅ Правильный паттерн (эталон)

### Примеры правильной реализации:
- ✅ `apps/web/routes/owner_timeslots.py`
- ✅ `apps/web/routes/moderator.py`
- ✅ `apps/web/routes/calendar.py`
- ✅ `apps/web/routes/admin_notifications.py` (после исправления)

### Код:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session  # ✅ Правильный импорт

@router.get("/some-route")
async def some_route(
    request: Request,
    current_user: dict = Depends(require_role),
    db: AsyncSession = Depends(get_db_session)  # ✅ Dependency injection
):
    """Описание роута"""
    try:
        # ✅ Используем db напрямую, без async with
        service = SomeService(db)
        result = await service.do_something()
        
        return templates.TemplateResponse("template.html", {
            "request": request,
            "current_user": current_user,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
```

---

## ❌ Неправильный паттерн (требует исправления)

```python
from core.database.session import get_async_session  # ❌ Неправильный импорт

@router.get("/some-route")
async def some_route(
    request: Request,
    current_user: dict = Depends(require_role)  # ❌ Нет db параметра
):
    """Описание роута"""
    try:
        # ❌ Создаем новое соединение вручную
        async with get_async_session() as session:
            service = SomeService(session)
            result = await service.do_something()
            
            return templates.TemplateResponse("template.html", {
                "request": request,
                "current_user": current_user,
                "result": result
            })
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
```

---

## 📝 Пошаговое руководство по исправлению

### Шаг 1: Изменить импорт

```python
# ❌ Было:
from core.database.session import get_async_session

# ✅ Стало:
from core.database.session import get_db_session
```

### Шаг 2: Добавить параметр db

```python
# ❌ Было:
async def route(
    request: Request,
    current_user: dict = Depends(require_role)
):

# ✅ Стало:
async def route(
    request: Request,
    current_user: dict = Depends(require_role),
    db: AsyncSession = Depends(get_db_session)  # Добавлено
):
```

### Шаг 3: Убрать async with и исправить отступы

```python
# ❌ Было:
    try:
        async with get_async_session() as session:
            service = Service(session)
            
            # код с двойными отступами
            result = await service.method()
            
            return response

# ✅ Стало:
    try:
        service = Service(db)
        
        # код с правильными отступами
        result = await service.method()
        
        return response
```

### Шаг 4: Заменить session на db

```python
# ❌ Было:
service = Service(session)

# ✅ Стало:
service = Service(db)
```

---

## 📋 Файлы, требующие исправления

### Высокий приоритет (часто используемые):
1. `apps/web/routes/owner.py` (37 использований)
2. `apps/web/routes/manager.py` (26 использований)
3. `apps/web/routes/admin.py` (10 использований)
4. `apps/web/routes/admin_reports.py` (10 использований)

### Средний приоритет:
5. `apps/web/routes/manager_timeslots.py` (8 использований)
6. `apps/web/routes/tariffs.py` (8 использований)
7. `apps/web/routes/limits.py` (9 использований)
8. `apps/web/routes/billing.py` (8 использований)

### Низкий приоритет:
9. `apps/web/routes/user_subscriptions.py` (6 использований)
10. `apps/web/routes/templates.py` (6 использований)
11. `apps/web/routes/shifts.py` (5 использований)
12. `apps/web/routes/auth.py` (5 использований)
13. `apps/web/routes/owner_shifts.py` (5 использований)
14. `apps/web/routes/employees.py` (4 использований)
15. `apps/web/routes/profile.py` (4 использований)
16. `apps/web/routes/dashboard.py` (4 использований)
17. `apps/web/routes/reports.py` (3 использований)
18. `apps/web/routes/employee.py` (2 использования)

---

## 🔍 Проверка после исправления

### Команда для поиска оставшихся проблем:

```bash
# Найти все использования get_async_session в роутах
grep -r "async with get_async_session" apps/web/routes/

# Подсчитать количество
grep -r "async with get_async_session" apps/web/routes/ | wc -l
```

### Линтер:

```bash
# Проверить конкретный файл
pylint apps/web/routes/your_file.py

# Или через IDE
# Read lints для проверки отступов и других ошибок
```

---

## ⚠️ Важные замечания

1. **НЕ ТРОГАТЬ** файлы вне `apps/web/routes/`
   - В скриптах, Celery задачах, тестах `get_async_session()` используется правильно
   - Проблема только в веб-роутах FastAPI

2. **НЕ ИЗМЕНЯТЬ** сервисы
   - Сервисы остаются без изменений
   - Меняется только способ передачи им сессии

3. **ПРОВЕРЯТЬ** отступы
   - После удаления `async with` блока нужно уменьшить отступы
   - Используйте автоформатирование (Black)

4. **ТЕСТИРОВАТЬ** после каждого файла
   - Запустить приложение
   - Проверить основные роуты
   - Убедиться в отсутствии ошибок

---

## 📊 Прогресс исправления

| Статус | Файлов | Использований | % |
|--------|--------|---------------|---|
| ✅ Исправлено | 1 | 23 | 12.6% |
| ⏳ В работе | 0 | 0 | 0% |
| 🔴 Осталось | 18 | 160 | 87.4% |

---

## 🎯 Рекомендуемый план

### Этап 1: Критичные файлы (1-2 дня)
- `owner.py`, `manager.py`, `admin.py`, `admin_reports.py`
- **160 → 90 использований** (-70)

### Этап 2: Важные файлы (1 день)
- `manager_timeslots.py`, `tariffs.py`, `limits.py`, `billing.py`
- **90 → 57 использований** (-33)

### Этап 3: Остальные файлы (1 день)
- Все оставшиеся файлы
- **57 → 0 использований** (-57)

**Общее время:** 3-4 дня для полного рефакторинга

---

## 📌 Чеклист для каждого файла

- [ ] Изменен импорт: `get_async_session` → `get_db_session`
- [ ] Добавлен параметр `db: AsyncSession = Depends(get_db_session)` во все роуты
- [ ] Удалены все `async with get_async_session() as session:`
- [ ] Заменены все `session` → `db` в сервисах
- [ ] Исправлены отступы
- [ ] Проверен линтер (0 ошибок отступов)
- [ ] Протестирован основной функционал
- [ ] Создан коммит с описанием изменений

---

**Дата создания:** 13 октября 2025  
**Автор:** AI Assistant (Claude Sonnet 4.5)  
**Основано на:** Исправление Iteration 25, коммит `df4ef91`

