# Баг: Инверсия статусов задач v2 при закрытии смены

## Описание проблемы

При закрытии смены бот показывает **НЕПРАВИЛЬНЫЕ** статусы задач v2 (галочки/крестики):
- Задача 5: выполнена через "Мои задачи", в БД `is_completed=TRUE`, но при закрытии смены показана КАК НЕВЫПОЛНЕННАЯ ❌
- Задача 6: НЕ выполнена, в БД `is_completed=FALSE`, но при закрытии смены показана КАК ВЫПОЛНЕННАЯ ✅

## Данные из БД

```sql
 id | shift_id | template_id |   task_title   | is_completed |         completed_at          
----+----------+-------------+----------------+--------------+-------------------------------
  5 |      309 |           6 | Влажная уборка | t            | 2025-10-29 16:26:25.818294+00
  6 |      310 |           6 | Влажная уборка | f            |                               
```

## Корректность по источникам

- **БД (task_entries_v2):** ✅ ПРАВИЛЬНО
- **Веб-страница `/owner/tasks/entries`:** ✅ ПРАВИЛЬНО (читает из БД)
- **Бот при закрытии смены:** ❌ НЕПРАВИЛЬНО (инверсия)

## Корень проблемы

### Файл: `apps/bot/handlers_div/shift_handlers.py`

**Строки 573-586** - формирование кнопок для задач при закрытии смены:

```python
for idx, task in enumerate(shift_tasks):
    task_text = task.get('text') or task.get('task_text', 'Задача')
    is_mandatory = task.get('is_mandatory', True)
    requires_media = task.get('requires_media', False)
    
    icon = "⚠️" if is_mandatory else "⭐"
    media_icon = "📸 " if requires_media else ""
    check = "✓ " if idx in completed_tasks else "☐ "  # ❌ ПРОБЛЕМА ЗДЕСЬ!
    keyboard.append([
        InlineKeyboardButton(
            f"{check}{media_icon}{icon} {task_text[:30]}...",
            callback_data=f"complete_shift_task:{shift['id']}:{idx}"
        )
    ])
```

**Проблема в строке 580:**
```python
check = "✓ " if idx in completed_tasks else "☐ "
```

### Почему это неправильно?

1. **Legacy Tasks (v1):** статус хранится в `user_state.completed_tasks` (список индексов) ✅
2. **Tasks v2:** статус хранится в БД (`task_entries_v2.is_completed`) ❌ НЕ ПРОВЕРЯЕТСЯ!

Код проверяет только `completed_tasks` (индексы из state), но игнорирует `is_completed` из БД для Tasks v2!

### Правильная логика (используется в "Мои задачи")

В функции `_show_my_tasks_list` (строка 1745-1750) используется **ПРАВИЛЬНАЯ** логика:

```python
# Для Tasks v2 проверяем is_completed из базы, для legacy - из completed_tasks
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)

# Иконки
mandatory_icon = "⚠️" if is_mandatory else "⭐"
completed_icon = "✅ " if is_task_completed else ""
```

**Эта логика проверяет:**
- Для Tasks v2: `task.get('is_completed')` из БД ✅
- Для legacy: `idx in completed_tasks` из state ✅

## Решение

Заменить логику в `_handle_close_shift` (строка 580) на аналогичную из `_show_my_tasks_list`:

### До (НЕПРАВИЛЬНО):
```python
check = "✓ " if idx in completed_tasks else "☐ "
```

### После (ПРАВИЛЬНО):
```python
# Для Tasks v2 проверяем is_completed из базы, для legacy - из completed_tasks
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
check = "✓ " if is_task_completed else "☐ "
```

## Затронутые функции

1. **`_handle_close_shift`** (строки 411-702) - основной обработчик ❌ БАГ
2. **`_handle_complete_shift_task`** (строки 1059-1248) - переключение задачи ⚠️ НУЖНО ПРОВЕРИТЬ
3. **`_show_my_tasks_list`** (строки 1734-1815) - "Мои задачи" ✅ ПРАВИЛЬНО
4. **`_show_my_tasks_list_update`** (строки 1875-1952) - обновление списка ⚠️ НУЖНО ПРОВЕРИТЬ

## Начисления

### Задача 5 (выполнена):
```sql
 id  | shift_id | adjustment_type | amount | description            | task_entry_v2_id | is_applied
-----+----------+-----------------+--------+------------------------+------------------+------------
 433 |          | task_bonus      | 100.00 | Задача: Влажная уборка |                5 | f
```
✅ Начисление создано правильно (Celery обработал is_completed=TRUE)

### Задача 6 (НЕ выполнена):
- Начислений нет ✅ (правильно, т.к. is_completed=FALSE)

## Выводы

1. **Celery работает правильно** - создает начисления только для выполненных задач (is_completed=TRUE)
2. **Веб-интерфейс работает правильно** - читает статусы из БД
3. **Бот "Мои задачи" работает правильно** - проверяет is_completed для Tasks v2
4. **Бот "Закрытие смены" работает НЕПРАВИЛЬНО** - игнорирует is_completed для Tasks v2

## План исправления

1. ✅ Идентифицировать все места с аналогичной проблемой
2. ✅ Исправить логику в `_handle_close_shift` (строка 580-582)
3. ✅ Проверить и исправить в `_handle_complete_shift_task` (строки 1143-1145, 1171-1173)
4. ✅ Проверить и исправить в `_show_my_tasks_list_update` (строки 1893-1895, 1919-1921)
5. ⏳ Протестировать на дэве (создать новую смену и проверить статусы)
6. ✅ Закоммитить изменения (commit: cb1fdc6)

## Внесенные изменения

### Исправленные места:

1. **`_handle_close_shift`** (строки 580-582):
```python
# До
check = "✓ " if idx in completed_tasks else "☐ "

# После
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
check = "✓ " if is_task_completed else "☐ "
```

2. **`_handle_complete_shift_task`** (строки 1143-1145):
```python
# До
completed_icon = "✅ " if idx in completed_tasks else ""

# После
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
completed_icon = "✅ " if is_task_completed else ""
```

3. **`_handle_complete_shift_task`** (строки 1171-1173):
```python
# До
check = "✓ " if idx in completed_tasks else "☐ "

# После
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
check = "✓ " if is_task_completed else "☐ "
```

4. **`_show_my_tasks_list_update`** (строки 1893-1895):
```python
# До
completed_icon = "✅ " if idx in completed_tasks else ""

# После
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
completed_icon = "✅ " if is_task_completed else ""
```

5. **`_show_my_tasks_list_update`** (строки 1919-1921):
```python
# До
check = "✓ " if idx in completed_tasks else "☐ "

# После
is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
check = "✓ " if is_task_completed else "☐ "
```

## Тестирование

Для проверки исправления:
1. Создать новый план задач v2 (например, plan_id=3)
2. Открыть смену (shift_id=311+)
3. Выполнить одну задачу через "Мои задачи" (должна получить is_completed=TRUE в БД)
4. Начать закрытие смены - проверить, что выполненная задача отображается с галочкой ✅
5. Не выполнять вторую задачу
6. Закрыть смену - проверить, что невыполненная задача отображается без галочки ❌
7. Проверить начисления в `/owner/payroll/adjustments`

