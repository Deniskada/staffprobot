# Полный список ошибок в _handle_received_task_v2_media

**Дата:** 29.10.2025  
**Коммит с ошибками:** `71c8fd5` (27.10.2025)  
**Функция:** `apps/bot/handlers_div/shift_handlers.py:_handle_received_task_v2_media`

---

## 🐛 Найденные ошибки (3 штуки)

### Ошибка 1: Неправильный импорт (ИСПРАВЛЕНА ✅)
**Строка:** 2357  
**Было:**
```python
from domain.entities.org_unit import OrgStructureUnit
```
**Должно быть:**
```python
from domain.entities.org_structure import OrgStructureUnit
```
**Статус:** ✅ Исправлено пользователем

---

### Ошибка 2: Неправильное название поля объекта
**Строка:** 2412  
**Ошибка из логов:**
```
AttributeError: 'Object' object has no attribute 'telegram_chat_id'
```

**Было:**
```python
telegram_chat_id = obj.telegram_chat_id  # ❌
```

**Должно быть:**
```python
telegram_chat_id = obj.telegram_report_chat_id  # ✅
```

**Правильное название:**
```sql
-- domain/entities/object.py
telegram_report_chat_id = Column(String(100), nullable=True)
```

---

### Ошибка 3: Неправильное название поля division
**Строка:** 2420  
**Аналогичная ошибка** (если дойдет до этой строки)

**Было:**
```python
telegram_chat_id = division.telegram_chat_id  # ❌
```

**Должно быть:**
```python
telegram_chat_id = division.telegram_report_chat_id  # ✅
```

**Правильное название:**
```sql
-- domain/entities/org_structure.py
telegram_report_chat_id = Column(String(100), nullable=True)
```

---

### Ошибка 4 (бонус): Проблема с логированием
**Строка:** 2501  
**Проблема:**
```python
logger.error(f"Error in _handle_received_task_v2_media: {e}", exc_info=True)
```

**KeyError:** "Attempt to overwrite 'exc_info' in LogRecord"

**Причина:** Конфликт в передаче `exc_info` в kwargs

**Исправление:**
```python
logger.error(f"Error in _handle_received_task_v2_media: {e}")
# Или
logger.exception(f"Error in _handle_received_task_v2_media: {e}")
```

---

## 📋 Список всех исправлений

**Файл:** `apps/bot/handlers_div/shift_handlers.py`

**4 изменения:**

1. **Строка 2357:**
   ```python
   # БЫЛО: from domain.entities.org_unit import OrgStructureUnit
   # СТАНЕТ: from domain.entities.org_structure import OrgStructureUnit
   ```
   ✅ УЖЕ ИСПРАВЛЕНО

2. **Строка 2412:**
   ```python
   # БЫЛО: telegram_chat_id = obj.telegram_chat_id
   # СТАНЕТ: telegram_chat_id = obj.telegram_report_chat_id
   ```
   ❌ ТРЕБУЕТСЯ ИСПРАВИТЬ

3. **Строка 2420:**
   ```python
   # БЫЛО: telegram_chat_id = division.telegram_chat_id
   # СТАНЕТ: telegram_chat_id = division.telegram_report_chat_id
   ```
   ❌ ТРЕБУЕТСЯ ИСПРАВИТЬ

4. **Строка 2501:**
   ```python
   # БЫЛО: logger.error(f"...", exc_info=True)
   # СТАНЕТ: logger.exception(f"...")
   ```
   ⚠️ РЕКОМЕНДУЕТСЯ (необязательно)

---

## 🔍 Как работает в других местах

**Правильный пример (строка 504-512):**
```python
# Получаем telegram_report_chat_id для медиа отчетов (наследование)
telegram_chat_id = None
if not obj.inherit_telegram_chat and obj.telegram_report_chat_id:  # ✅
    telegram_chat_id = obj.telegram_report_chat_id  # ✅
elif obj.org_unit:
    org_unit = obj.org_unit
    while org_unit:
        if org_unit.telegram_report_chat_id:  # ✅
            telegram_chat_id = org_unit.telegram_report_chat_id  # ✅
            break
        org_unit = org_unit.parent
```

**Этот код можно СКОПИРОВАТЬ** вместо строк 2410-2420!

---

## 💡 Рекомендация

**Вместо исправления отдельных строк** - скопировать рабочую логику из строк 502-512!

**Было (строки 2410-2420):**
```python
if obj:
    object_name = obj.name
    telegram_chat_id = obj.telegram_chat_id  # ❌
    
    # Если нет в объекте - ищем в division
    if not telegram_chat_id and obj.division_id:
        division_query = select(OrgStructureUnit).where(OrgStructureUnit.id == obj.division_id)
        division_result = await session.execute(division_query)
        division = division_result.scalar_one_or_none()
        if division:
            telegram_chat_id = division.telegram_chat_id  # ❌
```

**Станет (копия из строк 502-512):**
```python
if obj:
    object_name = obj.name
    # Получаем telegram_report_chat_id для медиа отчетов (наследование)
    telegram_chat_id = None
    if not obj.inherit_telegram_chat and obj.telegram_report_chat_id:
        telegram_chat_id = obj.telegram_report_chat_id
    elif obj.org_unit:
        org_unit = obj.org_unit
        while org_unit:
            if org_unit.telegram_report_chat_id:
                telegram_chat_id = org_unit.telegram_report_chat_id
                break
            org_unit = org_unit.parent
```

---

## ✅ После исправления

**Перезапустить бот:**
```bash
docker compose -f docker-compose.dev.yml restart bot
```

**Повторить тест:**
1. Мои задачи
2. Нажать галочку
3. Отправить фото
4. Бот должен ответить: "✅ Фотоотчёт отправлен"

---

**Статус:** ❌ Найдено 3 ошибки в одной функции, все из коммита 71c8fd5  
**Автор:** AI Assistant


