# Задачи на смену (Shift Tasks)

## Описание

Система задач, которые сотрудник должен выполнить во время смены. Поддерживает обязательные и необязательные задачи, автоматические штрафы/премии за выполнение/невыполнение.

## Модели данных

### 1. ShiftTask (Задача смены)

**Таблица:** `shift_tasks`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `shift_id` | Integer | FK → shifts.id |
| `task_text` | Text | Описание задачи |
| `is_completed` | Boolean | Выполнена ли задача |
| `completed_at` | DateTime | Дата/время выполнения |
| `source` | String(50) | object / timeslot / manual |
| `source_id` | Integer | ID источника (объекта/тайм-слота) |
| `is_mandatory` | Boolean | Обязательная задача |
| `deduction_amount` | Numeric(10,2) | Сумма штрафа/премии |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id |

### 2. TimeslotTaskTemplate (Шаблон задачи для тайм-слота)

**Таблица:** `timeslot_task_templates`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `timeslot_id` | Integer | FK → time_slots.id |
| `task_text` | Text | Описание задачи |
| `is_mandatory` | Boolean | Обязательная задача |
| `deduction_amount` | Numeric(10,2) | Сумма штрафа/премии |
| `display_order` | Integer | Порядок отображения |
| `created_at` | DateTime | Дата создания |
| `created_by_id` | Integer | FK → users.id |

## Логика работы

### Источники задач (приоритет)

1. **Тайм-слот** → `timeslot_task_templates` (переопределяет объект)
2. **Объект** → `object.shift_tasks` (JSONB, по умолчанию)
3. **Ручное добавление** → управляющий/владелец

### Структура shift_tasks в Object
```json
[
  {
    "text": "Проверить оборудование",
    "is_mandatory": true,
    "deduction_amount": -100  // Штраф за невыполнение
  },
  {
    "text": "Сделать фото отчет",
    "is_mandatory": false,
    "deduction_amount": 50  // Премия за выполнение
  }
]
```

## Процесс смены

### 1. Открытие смены
```python
from apps.web.services.shift_task_service import ShiftTaskService

# Создаются задачи из тайм-слота (если есть) или объекта
await shift_task_service.create_tasks_for_shift(
    shift_id=100,
    object_id=9,
    timeslot_id=1165  # или None
)
```

### 2. Выполнение задач (в боте)
Сотрудник видит список задач:
```
✅ Проверить оборудование (обязательная)
☐ Сделать фото отчет (необязательная)
```

Может отметить задачу как выполненную → `is_completed = True`, `completed_at = now()`

### 3. Закрытие смены
При закрытии смены проверяются невыполненные задачи:
```python
incomplete_tasks = await shift_task_service.get_incomplete_tasks(shift_id)

# Celery задача обработает их позже
```

### 4. Автоматические удержания (Celery)
**Задача:** `process_automatic_deductions()` (01:00 ежедневно)

**Логика для задач (только для "Повременно-премиальная"):**
- **Обязательная НЕ выполнена** → `deduction_amount < 0` → штраф
  - Создается `PayrollDeduction` с `is_automatic=True`
- **Необязательная выполнена** → `deduction_amount > 0` → премия
  - Создается `PayrollBonus` с `is_automatic=True`

## Типы задач

### Обязательная (`is_mandatory=True`)
- **Цель:** Задачи, которые ДОЛЖНЫ быть выполнены
- **Штраф:** Если не выполнена → `abs(deduction_amount)` удерживается
- **Пример:** "Проверить оборудование", "Сделать инвентаризацию"

### Необязательная (`is_mandatory=False`)
- **Цель:** Дополнительные задачи за премию
- **Премия:** Если выполнена → `deduction_amount` начисляется
- **Пример:** "Сделать фото отчет", "Убрать территорию"

## UI

### Для владельца/управляющего

#### В форме редактирования объекта
```html
<h5>Задачи на смене по умолчанию</h5>
<div class="task-item">
  <input name="task_texts[]" placeholder="Описание задачи">
  <input name="task_deductions[]" placeholder="Премия (₽)">
  <input type="checkbox" name="task_mandatory[]"> Обязательная
</div>
[+ Добавить задачу]
```

#### Страница `/owner/shift-tasks`
- Список всех задач по всем сменам
- Фильтры: объект, выполнение (выполнена/нет), обязательность
- Столбцы: Смена, Объект, Задача, Обязательность, Начисления (цветовая кодировка)

### Для сотрудника (в боте)

При закрытии смены:
```
📋 Задачи на смене:
✅ Проверить оборудование
☐ Сделать фото отчет

[✓ Отметить выполненными] [Продолжить закрытие]
```

## Сервис: ShiftTaskService

### Методы
```python
# Создать задачи для смены
create_tasks_for_shift(shift_id, object_id, timeslot_id)

# Получить задачи смены
get_shift_tasks(shift_id) -> List[ShiftTask]

# Отметить выполненной
mark_task_completed(task_id) -> ShiftTask

# Получить невыполненные
get_incomplete_tasks(shift_id) -> List[ShiftTask]

# Получить выполненные
get_completed_tasks(shift_id) -> List[ShiftTask]
```

## Интеграция с начислениями

### Связь через Celery
```python
# В process_automatic_deductions()
for shift in completed_shifts:
    incomplete_tasks = await shift_task_service.get_incomplete_tasks(shift.id)
    
    for task in incomplete_tasks:
        if task.is_mandatory and task.deduction_amount < 0:
            # Создать штраф
            await payroll_service.add_deduction(...)
    
    completed_optional = [t for t in all_tasks if not t.is_mandatory and t.is_completed]
    for task in completed_optional:
        if task.deduction_amount > 0:
            # Создать премию
            await payroll_service.add_bonus(...)
```

## Индексы

- `idx_shift_tasks_shift_id` - для поиска по смене
- `idx_shift_tasks_is_completed` - для фильтрации
- `idx_shift_tasks_is_mandatory` - для фильтрации
- `idx_timeslot_task_templates_timeslot_id` - для поиска по тайм-слоту

## См. также

- [Смены](shifts.md)
- [Объекты](objects.md)
- [Тайм-слоты](timeslots.md)
- [Начисления и выплаты](payroll.md)

