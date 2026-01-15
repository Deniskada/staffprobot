# План восстановления функционала задач

**Дата:** 29.10.2025  
**Проблема:** Задачи не показываются при открытии смены  
**Решение:** Восстановить `_collect_shift_tasks` с поддержкой Tasks v2 + legacy fallback

---

## 🎯 Цель

Восстановить работу задач в 100% случаев, поддерживая:
1. ✅ Tasks v2 (новая система) - приоритет
2. ✅ object.shift_tasks (legacy JSONB) - fallback
3. ✅ timeslot.task_templates (legacy table) - fallback

---

## 📋 План действий

### Этап 1: Извлечение рабочего кода из main (30 мин)

**Файлы для изучения:**
```bash
# 1. Функция _collect_shift_tasks
git show main:apps/bot/handlers_div/shift_handlers.py | grep -A150 "^async def _collect_shift_tasks"

# 2. Функция _load_timeslot_tasks
git show main:apps/bot/handlers_div/shift_handlers.py | grep -A60 "^async def _load_timeslot_tasks"
```

**Что восстановить:**
- `async def _collect_shift_tasks()` (~120 строк)
- `async def _load_timeslot_tasks()` (~60 строк)

---

### Этап 2: Адаптация для Tasks v2 (1 час)

**Модификация `_collect_shift_tasks`:**

```python
async def _collect_shift_tasks(
    session: AsyncSession,
    shift: Shift,
    timeslot: Optional[TimeSlot] = None,
    object_: Optional[Object] = None
) -> List[Dict]:
    """
    Собрать задачи из всех источников с приоритетом Tasks v2.
    
    Приоритет источников:
    1. Tasks v2 (TaskEntryV2) - если существуют
    2. Legacy object.shift_tasks (JSONB) - fallback
    3. Legacy timeslot.task_templates (таблица) - fallback
    """
    all_tasks = []
    
    # ====================================================================
    # ПРИОРИТЕТ 1: Tasks v2 (новая система)
    # ====================================================================
    try:
        from shared.services.task_service import TaskService
        task_service = TaskService(session)
        task_v2_entries = await task_service.get_entries_for_shift(shift.id)
        
        if task_v2_entries:
            logger.info(f"Using Tasks v2: found {len(task_v2_entries)} entries for shift {shift.id}")
            
            for entry in task_v2_entries:
                # Унифицированный формат для совместимости с существующим кодом бота
                all_tasks.append({
                    'text': entry.template.title,
                    'is_mandatory': entry.template.is_mandatory,
                    'deduction_amount': float(entry.template.default_bonus_amount or 0),
                    'requires_media': entry.template.requires_media,
                    'source': 'tasks_v2',
                    'entry_id': entry.id,  # Для отметки выполнения
                    'template_id': entry.template_id
                })
            
            return all_tasks  # Если есть Tasks v2 - используем только их!
    
    except Exception as e:
        logger.error(f"Error loading Tasks v2: {e}", exc_info=True)
        # Продолжаем fallback на legacy
    
    # ====================================================================
    # FALLBACK 1: Legacy timeslot.task_templates (если есть)
    # ====================================================================
    if timeslot and timeslot.task_templates:
        # Проверяем флаг ignore_object_tasks
        if not timeslot.ignore_object_tasks:
            logger.info(f"Using legacy timeslot tasks for shift {shift.id}")
            timeslot_tasks = await _load_timeslot_tasks(session, timeslot)
            all_tasks.extend(timeslot_tasks)
            return all_tasks  # Если есть timeslot - используем только их
    
    # ====================================================================
    # FALLBACK 2: Legacy object.shift_tasks (JSONB)
    # ====================================================================
    if object_ and object_.shift_tasks:
        try:
            shift_tasks_data = object_.shift_tasks
            
            if isinstance(shift_tasks_data, list):
                logger.info(f"Using legacy object.shift_tasks for shift {shift.id}: {len(shift_tasks_data)} tasks")
                
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
    
    logger.info(f"Collected {len(all_tasks)} tasks total for shift {shift.id}")
    return all_tasks
```

**Ключевые изменения:**
- ✅ Добавлен блок Tasks v2 с приоритетом 1
- ✅ Сохранены legacy fallbacks
- ✅ Унифицированный формат для совместимости с ботом
- ✅ Логирование для отладки

---

### Этап 3: Интеграция в обработчики (30 мин)

**Файл:** `apps/bot/handlers_div/shift_handlers.py`

**Изменения в `_handle_my_tasks`:**
```python
# БЫЛО (feature):
task_service = TaskService(session)
task_entries = await task_service.get_entries_for_shift(shift.id)

# СТАНЕТ:
shift_tasks = await _collect_shift_tasks(
    session=session,
    shift=shift_obj,
    timeslot=timeslot,
    object_=obj
)
```

**Изменения в `_handle_close_shift`:**
```python
# Аналогично - заменить на _collect_shift_tasks
```

**Изменения в `_handle_open_shift`:**
```python
# После создания смены показываем задачи через _collect_shift_tasks
```

---

### Этап 4: Обработка выполнения задач (30 мин)

**Проблема:** Задачи из разных источников имеют разные ID

**Решение:**
```python
# При отметке задачи проверяем source:
if task['source'] == 'tasks_v2':
    # Обновляем TaskEntryV2
    entry = await session.get(TaskEntryV2, task['entry_id'])
    entry.is_completed = True
    entry.completed_at = datetime.utcnow()
    
elif task['source'] in ['object_legacy', 'timeslot_legacy']:
    # Сохраняем в UserState для последующей обработки в Celery
    # (как было в main)
    pass
```

---

### Этап 5: Тестирование (30 мин)

**Сценарии:**

1. **Смена на объекте С TaskPlanV2:**
   - Создать TaskPlanV2 для объекта 3
   - Открыть смену на объекте 3
   - Проверить что задачи из Tasks v2 показываются ✅

2. **Смена на объекте БЕЗ TaskPlanV2, но с object.shift_tasks:**
   - Добавить задачи в object.shift_tasks для объекта 1
   - Открыть смену на объекте 1
   - Проверить что legacy задачи показываются ✅

3. **Закрытие смены с задачами:**
   - Открыть смену → показать задачи
   - Отметить некоторые задачи
   - Закрыть смену
   - Проверить что задачи сохранены ✅

---

## 📊 Затронутые файлы

**Изменения:**
- `apps/bot/handlers_div/shift_handlers.py` (+200 строк)
  - Восстановить `_collect_shift_tasks`
  - Восстановить `_load_timeslot_tasks`
  - Изменить `_handle_my_tasks`
  - Изменить `_handle_close_shift`

**БЕЗ изменений:**
- `apps/bot/services/shift_service.py` (создание задач v2 остаётся)
- `core/celery/tasks/task_assignment.py` (логика v2 остаётся)
- `shared/services/task_service.py` (сервис v2 остаётся)

---

## 🎯 Итоговый результат

**После восстановления:**
- ✅ Задачи работают на объектах С планами (Tasks v2)
- ✅ Задачи работают на объектах БЕЗ планов (legacy fallback)
- ✅ Плавная миграция с legacy на v2 (по мере создания планов)
- ✅ Обратная совместимость сохранена

---

**Статус:** ⏳ Требуется утверждение пользователя  
**Автор:** AI Assistant


