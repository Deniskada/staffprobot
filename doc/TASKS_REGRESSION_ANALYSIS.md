# Анализ регрессии: Задачи не создаются при открытии смены

**Дата:** 29.10.2025  
**Проблема:** После мерджа feature/rules-tasks-incidents задачи не показываются в боте при открытии смены  
**Тип:** Регрессия функционала

---

## 🔍 Корневая причина

### Что было в main (рабочая версия):

**Логика задач:**
```python
# apps/bot/handlers_div/shift_handlers.py (main)
async def _collect_shift_tasks(session, shift, timeslot, object_):
    """Собрать задачи из нескольких источников"""
    
    # 1. Задачи из timeslot.task_templates (если есть)
    # 2. Задачи из object.shift_tasks (JSONB) - ВСЕГДА работало
    # 3. Объединить и вернуть
```

**При открытии смены (main):**
- Задачи НЕ сохранялись в БД
- Задачи загружались на лету из `object.shift_tasks` JSONB
- Показывались в боте через UserState
- Сохранялись в БД только при закрытии смены через Celery

**Результат:** Задачи работали в 100% случаев (если были в object.shift_tasks)

---

### Что стало в feature/rules-tasks-incidents (сломанная версия):

**Коммит:** `c6b054a` - "архитектурная унификация Tasks v2 через shift_id"

**Изменения:**
```python
# apps/bot/handlers_div/shift_handlers.py (feature)
# Функция _collect_shift_tasks УДАЛЕНА!

# Вместо неё:
task_service = TaskService(session)
task_entries = await task_service.get_entries_for_shift(shift.id)
# ↑ Ищет ТОЛЬКО в таблице task_entries_v2
```

**При открытии смены (feature):**
- Вызывается `create_task_entries_for_shift()` в `shift_service.py:327`
- Эта функция ищет `TaskPlanV2` для объекта смены
- **ЕСЛИ плана НЕТ** → задачи НЕ создаются → список пуст
- **ЕСЛИ план ЕСТЬ** → создаётся `TaskEntryV2` → задачи показываются

**Результат:** Задачи работают ТОЛЬКО если есть TaskPlanV2 для объекта

---

## 📊 Примеры

### Смена 565, 566 (object_id=9) - РАБОТАЮТ ✅
```sql
SELECT id, object_id FROM shift_schedules WHERE id IN (565, 566);
-- object_id = 9

SELECT * FROM task_plans_v2;
-- plan для object_id = 9 СУЩЕСТВУЕТ ✅

SELECT * FROM task_entries_v2 WHERE shift_schedule_id IN (565, 566);
-- 2 записи созданы ✅
```

### Смена 306 (object_id=3) - НЕ РАБОТАЮТ ❌
```sql
SELECT id, object_id FROM shift_schedules WHERE id = 306;
-- object_id = 3

SELECT * FROM task_plans_v2 WHERE object_ids @> '[3]';
-- НЕТ плана для object_id = 3 ❌

SELECT * FROM task_entries_v2 WHERE shift_schedule_id = 306;
-- 0 записей ❌
```

---

## 🎯 Что сломалось

### 1. Удалена функция `_collect_shift_tasks`
**Файл:** `apps/bot/handlers_div/shift_handlers.py`  
**Коммит:** `c6b054a`  
**Что делала:** Собирала задачи из:
- `timeslot.task_templates` (приоритет 1)
- `object.shift_tasks` JSONB (приоритет 2, ВСЕГДА работало)
- Возвращала унифицированный список

**Что заменило:** 
```python
task_service.get_entries_for_shift(shift.id)
# ↑ Возвращает ТОЛЬКО задачи из task_entries_v2
```

### 2. Потеряна поддержка object.shift_tasks (legacy)
**Проблема:** Код больше НЕ читает `object.shift_tasks`  
**Последствие:** Старые задачи (если были) игнорируются  
**Критичность:** ВЫСОКАЯ (функционал сломан для объектов без TaskPlanV2)

### 3. Задачи создаются только при наличии плана
**Логика:** `create_task_entries_for_shift` в `shift_service.py:327`  
**Ищет:** `TaskPlanV2` с `object_id = shift.object_id`  
**Если НЕТ плана:** задачи не создаются  
**Проблема:** У большинства объектов нет планов (мы только что всё очистили!)

---

## 💡 Решения

### ✅ Вариант 1: Восстановить _collect_shift_tasks с поддержкой обоих источников (РЕКОМЕНДУЕТСЯ)

**Что сделать:**
1. Восстановить функцию `_collect_shift_tasks` из main
2. Модифицировать её для поддержки Tasks v2:
   ```python
   async def _collect_shift_tasks(session, shift, timeslot, object_):
       # Приоритет 1: Tasks v2 (если есть)
       task_v2_entries = await task_service.get_entries_for_shift(shift.id)
       if task_v2_entries:
           return [format_task_v2(e) for e in task_v2_entries]
       
       # Fallback: Legacy задачи из object.shift_tasks (для совместимости)
       if object_ and object_.shift_tasks:
           return format_legacy_tasks(object_.shift_tasks)
       
       # Fallback 2: Задачи из timeslot (еще старее)
       if timeslot and timeslot.task_templates:
           return await load_timeslot_tasks(session, timeslot)
       
       return []
   ```

**Плюсы:**
- ✅ Обратная совместимость с object.shift_tasks
- ✅ Задачи работают даже без TaskPlanV2
- ✅ Плавный переход на Tasks v2

**Минусы:**
- Нужно восстановить ~100 строк кода
- Поддержка legacy формата

---

### ⚠️ Вариант 2: Создать TaskPlanV2 для всех объектов с legacy задачами

**Что сделать:**
1. Найти все объекты с `shift_tasks != []`
2. Для каждого создать TaskTemplateV2 из shift_tasks
3. Создать TaskPlanV2 для каждого объекта

**Плюсы:**
- Чистое решение (только Tasks v2)
- Нет legacy кода

**Минусы:**
- ❌ Задачи были очищены! (мы только что удалили object.shift_tasks)
- ❌ Нет данных для миграции
- ❌ Не решает проблему для новых объектов без планов

---

### ❌ Вариант 3: Откатить коммит c6b054a

**Минусы:**
- Потеряем всю работу по Tasks v2
- Откатятся другие исправления

---

## 📋 Рекомендуемый план восстановления (Вариант 1)

### Шаг 1: Найти рабочую версию `_collect_shift_tasks`
```bash
git show main:apps/bot/handlers_div/shift_handlers.py > /tmp/main_shift_handlers.py
# Скопировать функцию _collect_shift_tasks (около 120 строк)
```

### Шаг 2: Адаптировать для Tasks v2 (модифицировать)
```python
async def _collect_shift_tasks(session, shift, timeslot, object_):
    """
    Приоритет источников задач:
    1. Tasks v2 (TaskEntryV2) - если есть
    2. Legacy object.shift_tasks - fallback
    3. Legacy timeslot.task_templates - fallback
    """
    all_tasks = []
    
    # ==== НОВОЕ: Проверка Tasks v2 ====
    try:
        from shared.services.task_service import TaskService
        task_service = TaskService(session)
        task_v2_entries = await task_service.get_entries_for_shift(shift.id)
        
        if task_v2_entries:
            # Форматируем Tasks v2 в унифицированный формат
            for entry in task_v2_entries:
                all_tasks.append({
                    'text': entry.template.title,
                    'is_mandatory': entry.template.is_mandatory,
                    'deduction_amount': entry.template.default_bonus_amount or 0,
                    'requires_media': entry.template.requires_media,
                    'source': 'tasks_v2',
                    'entry_id': entry.id  # Для отметки выполнения
                })
            
            logger.info(f"Loaded {len(all_tasks)} tasks from Tasks v2")
            return all_tasks  # Если есть v2 - используем только их
    except Exception as e:
        logger.error(f"Error loading Tasks v2: {e}")
    
    # ==== FALLBACK: Legacy логика (из main) ====
    # 1. Timeslot tasks (если есть и не игнорируются)
    if timeslot and timeslot.task_templates:
        if not timeslot.ignore_object_tasks:
            tasks = await _load_timeslot_tasks(session, timeslot)
            all_tasks.extend(tasks)
            return all_tasks
    
    # 2. Object.shift_tasks (legacy JSONB)
    if object_ and object_.shift_tasks:
        try:
            shift_tasks_data = object_.shift_tasks
            if isinstance(shift_tasks_data, list):
                for task in shift_tasks_data:
                    all_tasks.append({
                        'text': task.get('text', ''),
                        'is_mandatory': task.get('is_mandatory', False),
                        'deduction_amount': task.get('deduction_amount', 0),
                        'requires_media': task.get('requires_media', False),
                        'source': 'object_legacy'
                    })
        except Exception as e:
            logger.error(f"Error parsing object.shift_tasks: {e}")
    
    return all_tasks
```

### Шаг 3: Восстановить вызовы в _handle_my_tasks и _handle_close_shift
```python
# В _handle_my_tasks:
shift_tasks = await _collect_shift_tasks(
    session=session,
    shift=shift_obj,
    timeslot=timeslot,
    object_=obj
)

# В _handle_close_shift:
shift_tasks = await _collect_shift_tasks(
    session=session,
    shift=shift_obj,
    timeslot=shift_obj.time_slot,
    object_=shift_obj.object
)
```

### Шаг 4: Тестирование
1. Открыть смену на объекте БЕЗ TaskPlanV2 → задачи из object.shift_tasks должны показаться
2. Открыть смену на объекте С TaskPlanV2 → задачи из Tasks v2 должны показаться
3. Проверить закрытие смены с задачами

---

## 🔗 Ключевые файлы для восстановления

**Откуда брать код (main):**
- `apps/bot/handlers_div/shift_handlers.py` - функция `_collect_shift_tasks` (строки ~150-270)
- `apps/bot/handlers_div/shift_handlers.py` - функция `_load_timeslot_tasks` (строки ~90-150)

**Куда интегрировать (feature):**
- `apps/bot/handlers_div/shift_handlers.py` - добавить обе функции
- `apps/bot/handlers_div/shift_handlers.py` - использовать в `_handle_my_tasks` и `_handle_close_shift`

**Коммиты для изучения:**
- `c6b054a` - где удалили _collect_shift_tasks
- `54e3bf3` - "использование _collect_shift_tasks в _handle_close_shift"
- `b6f0fcf` - "Создана функция _collect_shift_tasks()"

---

## ⚠️ Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Дублирование задач (v2 + legacy) | Средняя | Приоритет: сначала v2, потом legacy |
| Конфликт форматов задач | Низкая | Унифицированный формат dict |
| Регрессия в закрытии смены | Средняя | Тщательное тестирование |

---

## ✅ Критерии готовности

- [ ] Функция `_collect_shift_tasks` восстановлена
- [ ] Поддержка Tasks v2 добавлена (приоритет 1)
- [ ] Fallback на object.shift_tasks работает (приоритет 2)
- [ ] Fallback на timeslot.task_templates работает (приоритет 3)
- [ ] Задачи показываются в боте для любого объекта
- [ ] Закрытие смены работает с обоими типами задач
- [ ] Тестирование пройдено успешно

---

## 🚀 Ориентировочное время

- Восстановление кода: 1-2 часа
- Адаптация под Tasks v2: 1 час
- Тестирование: 30 минут

**Итого:** 2.5-3.5 часа

---

**Статус:** Требуется утверждение плана восстановления  
**Автор:** AI Assistant


