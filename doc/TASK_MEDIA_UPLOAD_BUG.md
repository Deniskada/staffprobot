# Ошибка: Бот не отвечает при отправке фото для задачи

**Дата:** 29.10.2025  
**Контекст:** Отправка фото через "Мои задачи" → запрос фотоотчёта  
**Статус:** 🐛 Найдена ошибка импорта

---

## 🔍 Ошибка из логов

### Основная ошибка (строка 909):
```python
File "/app/apps/bot/handlers_div/shift_handlers.py", line 2357
    from domain.entities.org_unit import OrgStructureUnit
ModuleNotFoundError: No module named 'domain.entities.org_unit'
```

**Проблема:** Неправильное имя модуля!

**Должно быть:**
```python
from domain.entities.org_structure_unit import OrgStructureUnit
```

**А написано:**
```python
from domain.entities.org_unit import OrgStructureUnit
```

### Вторичная ошибка (строка 934):
```python
KeyError: "Attempt to overwrite 'exc_info' in LogRecord"
```

**Проблема:** В обработчике ошибок (строка 2501) вызывается:
```python
logger.error(f"Error in _handle_received_task_v2_media: {e}", exc_info=True)
```

Но `exc_info` уже передан в kwargs, что вызывает конфликт в логировании.

---

## 📂 Где ошибка

**Файл:** `apps/bot/handlers_div/shift_handlers.py`  
**Функция:** `_handle_received_task_v2_media`  
**Строка:** 2357

**Контекст:**
```python
async def _handle_received_task_v2_media(...):
    try:
        # ...
        from domain.entities.org_unit import OrgStructureUnit  # ❌ СТРОКА 2357
        # ...
    except Exception as e:
        logger.error(f"Error in _handle_received_task_v2_media: {e}", exc_info=True)  # ❌ СТРОКА 2501
```

---

## 🎯 Откуда взялась ошибка

Проверим историю изменений:

**В main версии:**
```bash
git show main:apps/bot/handlers_div/shift_handlers.py | grep "org_unit\|OrgStructureUnit"
```

**Вероятные причины:**
1. Автозамена при рефакторинге (org_structure_unit → org_unit)
2. Копипаст из другого файла с неправильным импортом
3. Изменение при мердже feature ветки

---

## 🔧 Исправление

**Изменить строку 2357:**
```python
# БЫЛО (неправильно):
from domain.entities.org_unit import OrgStructureUnit

# ДОЛЖНО БЫТЬ:
from domain.entities.org_structure_unit import OrgStructureUnit
```

**Опционально (строка 2501):**
```python
# БЫЛО:
logger.error(f"Error in _handle_received_task_v2_media: {e}", exc_info=True)

# ЛУЧШЕ:
logger.error(f"Error in _handle_received_task_v2_media: {e}", exc_info=e)
```

---

## 📊 Проверка других файлов

**Ищем аналогичные ошибки:**
```bash
grep -r "from domain.entities.org_unit import" apps/
```

**Ожидается:** Нет других файлов с таким импортом (или все должны быть исправлены)

---

## ✅ Почему через "Закрытие смены" работало?

**В функции `_handle_close_shift`** (или другом обработчике закрытия):
- Скорее всего использует другой код без этого импорта
- Или импорт правильный: `from domain.entities.org_structure_unit import ...`

**Разница:**
- "Мои задачи" → вызывает `_handle_received_task_v2_media` → ОШИБКА ❌
- "Закрытие смены" → вызывает другой обработчик → работает ✅

---

## 📋 Как воспроизвести

1. Открыть смену
2. Нажать "📋 Мои задачи"
3. Нажать галочку на задаче с `requires_media=TRUE`
4. Отправить фото
5. **Результат:** Бот не отвечает, в логах ошибка импорта

---

## 🎯 Анализ завершён

### Когда появилась ошибка
**Коммит:** `71c8fd5` (27.10.2025)  
**Название:** "Интеграция Tasks v2 в бот: обработка выполнения задач с фото/видео отчётами"  
**Автор:** Deniskada

**Что произошло:**
При добавлении функции `_handle_received_task_v2_media` был использован неправильный импорт:
```python
from domain.entities.org_unit import OrgStructureUnit  # ❌
```

### Почему через "Закрытие смены" работало
**В том же файле (строка 452):**
```python
from domain.entities.org_structure import OrgStructureUnit  # ✅ ПРАВИЛЬНО
```

**Разница:**
- `_handle_close_shift` → использует импорт из строки 452 → работает ✅
- `_handle_received_task_v2_media` → использует импорт из строки 2357 → падает ❌

### Количество ошибок
**Найдено:** 1 неправильный импорт  
**Файл:** `apps/bot/handlers_div/shift_handlers.py:2357`  
**Других ошибок:** Не найдено

---

## 🔧 План исправления

**Изменить 1 строку:**
```python
# apps/bot/handlers_div/shift_handlers.py:2357

# БЫЛО:
from domain.entities.org_unit import OrgStructureUnit

# СТАНЕТ:
from domain.entities.org_structure import OrgStructureUnit
```

**Перезапустить:**
```bash
docker compose -f docker-compose.dev.yml restart bot
```

**Проверить:**
1. Открыть смену
2. Мои задачи → Отметить задачу → Отправить фото
3. Проверить `is_completed = TRUE` в БД
4. Вызвать `process_task_bonuses`
5. Проверить создание корректировки

---

**Статус:** ✅ Причина найдена - опечатка в импорте при коммите 71c8fd5  
**Исправление:** 1 строка  
**Автор:** AI Assistant




