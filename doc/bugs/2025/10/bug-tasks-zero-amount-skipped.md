# Bug: Обязательные задачи с amount=0 игнорируются

**ID:** bug-tasks-zero-amount-skipped  
**Дата обнаружения:** 2025-10-12  
**Статус:** ✅ Исправлено  
**Приоритет:** Высокий  
**Теги:** `celery`, `payroll`, `tasks`, `business-logic`

---

## 🐛 Симптомы

Обязательная задача "поцеловать в попу" не создает штраф при невыполнении:

```sql
-- Тайм-слот 1167 имеет задачу:
shift_tasks: [{"text": "поцеловать в попу", "bonus_amount": 0.0, "is_mandatory": true, ...}]

-- Смена 90 закрыта БЕЗ выполнения задачи
-- Но adjustment НЕ создан!

SELECT * FROM payroll_adjustments WHERE shift_id = 90;
-- Только 1 запись: shift_base (нет task_penalty!)
```

---

## 🔍 Воспроизведение

1. Создать тайм-слот с обязательной задачей, у которой `amount = 0` или `deduction_amount = 0`
2. Открыть и закрыть смену БЕЗ выполнения этой задачи
3. Celery создаст только `base_pay`, задача будет пропущена

**SQL для воспроизведения:**
```sql
UPDATE time_slots SET shift_tasks = '[{
  "text": "Тест задача", 
  "is_mandatory": true, 
  "deduction_amount": 0
}]'::jsonb WHERE id = 1167;
```

---

## 🔧 Корень проблемы

**Файл:** `core/celery/tasks/adjustment_tasks.py:226-231`

```python
task_text = task.get('text') or task.get('task_text', 'Задача')
is_mandatory = task.get('is_mandatory', True)
deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
requires_media = task.get('requires_media', False)

if not deduction_amount or float(deduction_amount) == 0:
    continue  # ❌ Пропускаем ВСЕ задачи без стоимости (даже обязательные!)
```

**Проблемы:**
1. Пропускаются ВСЕ задачи с amount=0, включая обязательные
2. Не поддерживается новый формат JSONB (`description`, `amount`)
3. Нет дефолтного штрафа для обязательных задач

---

## ✅ Решение

### 1. Поддержка старого и нового формата

```python
# Поддержка старого и нового формата
task_text = task.get('text') or task.get('description') or task.get('task_text', 'Задача')
is_mandatory = task.get('is_mandatory', True)

# Старый формат: deduction_amount, bonus_amount
# Новый формат: amount
amount_value = task.get('amount')
if amount_value is None:
    # Старый формат
    deduction = task.get('deduction_amount')
    bonus = task.get('bonus_amount')
    if deduction is not None:
        amount_value = deduction
    elif bonus is not None:
        amount_value = bonus
    else:
        amount_value = 0
```

### 2. Пропускаем только НЕобязательные задачи без стоимости

```python
# Пропускаем НЕобязательные задачи без стоимости
if (not amount_value or float(amount_value) == 0) and not is_mandatory:
    continue
```

### 3. Дефолтный штраф для обязательных задач

```python
# Для обязательных задач без стоимости используем дефолтный штраф -50₽
if is_mandatory and (not amount_value or float(amount_value) == 0):
    amount_value = -50
```

---

## 📦 Коммит

```
commit 75e91e7
Исправление обработки задач в adjustment_tasks

Проблемы:
1. Задачи с amount=0 пропускались, даже обязательные
2. Не поддерживался новый формат (amount вместо deduction_amount/bonus_amount)

Решения:
1. Обязательные задачи без стоимости получают дефолтный штраф -50₽
2. Поддержка обоих форматов: старого (text, deduction_amount, bonus_amount) и нового (description, amount)
3. НЕобязательные задачи без стоимости пропускаются (как и раньше)
```

---

## 🧪 Тестирование

**До исправления:**
```sql
-- Смена 90: 1 adjustment (только base)
SELECT COUNT(*) FROM payroll_adjustments WHERE shift_id = 90;
-- 1
```

**После исправления (для новых смен):**
```sql
-- Обязательная задача с amount=0 создает штраф -50₽
-- adjustment_type = 'task_penalty', amount = -50.00
```

---

## 📊 Форматы JSONB задач

### Старый формат (объекты):
```json
{
  "text": "Уборка помещения",
  "is_mandatory": true,
  "requires_media": true,
  "deduction_amount": -100.0
}
```

### Новый формат (тайм-слоты):
```json
{
  "description": "Тестовая задача",
  "is_mandatory": true,
  "requires_media": false,
  "amount": -100.0
}
```

**Оба формата теперь поддерживаются!**

---

## 📚 Связанные задачи

- Roadmap: Phase 4A - Payroll Adjustments Refactoring
- Roadmap: Phase 4C (Object State) - Task fields в тайм-слотах
- Testing: `tests/manual/OBJECT_STATE_AND_TIMESLOTS_TESTING.md` (Фаза 5.1.В-Г)

---

## 💡 Lessons Learned

1. **Бизнес-логика:** Обязательные задачи должны иметь последствия, даже без явной стоимости
2. **Миграция форматов:** При изменении JSONB структуры нужна обратная совместимость
3. **Дефолтные значения:** Явные дефолты лучше, чем пропуск операций

---

## 🔗 См. также

- `domain/entities/object.py` - структура `shift_tasks` для объектов
- `domain/entities/time_slot.py` - структура `shift_tasks` для тайм-слотов
- `apps/web/services/object_service.py` - создание задач в новом формате

