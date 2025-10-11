# Bug: Multiple rows error при проверке adjustments

**ID:** bug-adjustment-multiple-rows  
**Дата обнаружения:** 2025-10-12  
**Статус:** ✅ Исправлено  
**Приоритет:** Критичный  
**Теги:** `celery`, `payroll`, `database`, `sqlalchemy`

---

## 🐛 Симптомы

```
Error processing shift 89: Multiple rows were found when one or none was required
```

Celery задача `process_closed_shifts_adjustments` падает с ошибкой при обработке смен, у которых уже есть несколько adjustments.

---

## 🔍 Воспроизведение

1. Закрыть смену, для которой Celery уже создал adjustments (base_pay + task_penalty)
2. Подождать следующего запуска Celery (каждую минуту)
3. Celery попытается проверить существование adjustments и упадет с `MultipleResultsFound`

**Пример:**
```sql
SELECT * FROM payroll_adjustments WHERE shift_id = 89;
-- Возвращает 2 записи: base_pay и task_penalty
```

---

## 🔧 Корень проблемы

**Файл:** `core/celery/tasks/adjustment_tasks.py:76-80`

```python
existing_query = select(PayrollAdjustment).where(
    PayrollAdjustment.shift_id == shift.id
)
existing_result = await session.execute(existing_query)
existing = existing_result.scalar_one_or_none()  # ❌ ОШИБКА ЗДЕСЬ
```

**Проблема:** 
- `scalar_one_or_none()` ожидает 0 или 1 результат
- Для смены может быть несколько adjustments (base + penalties + bonuses)
- SQLAlchemy выбрасывает `MultipleResultsFound`

---

## ✅ Решение

Заменить `scalar_one_or_none()` на `scalars().first()`:

```python
existing_query = select(PayrollAdjustment).where(
    PayrollAdjustment.shift_id == shift.id
)
existing_result = await session.execute(existing_query)
existing = existing_result.scalars().first()  # ✅ Берет первый или None
```

**Логика:**
- Нам нужно только проверить существование хотя бы одного adjustment
- `first()` возвращает первый результат или `None` без ошибки
- Если есть хотя бы один adjustment - смену пропускаем

---

## 📦 Коммит

```
commit c1a0015
Исправление ошибки Multiple rows в adjustment_tasks

Проблема: scalar_one_or_none() падал с ошибкой, если у смены несколько adjustments
Решение: использовать scalars().first() для проверки существования
```

---

## 🧪 Тестирование

**До исправления:**
```bash
docker compose -f docker-compose.dev.yml logs celery_worker | grep "Multiple rows"
# Error processing shift 89: Multiple rows were found...
```

**После исправления:**
```bash
# Adjustments already exist for shift 89, skipping
# Task succeeded: {'shifts_processed': 0, 'adjustments_created': 0}
```

---

## 📚 Связанные задачи

- Roadmap: Phase 4A - Payroll Adjustments Refactoring
- Testing: `tests/manual/OBJECT_STATE_AND_TIMESLOTS_TESTING.md` (Фаза 5.1)

---

## 💡 Lessons Learned

1. **SQLAlchemy API:** `scalar_one_or_none()` строгий - падает при множественных результатах
2. **Проверка существования:** Для `exists()` логики использовать `first()` или `count()`
3. **Celery логирование:** Важно логировать не только ошибки, но и skip'ы операций

---

## 🔗 См. также

- SQLAlchemy 2.0 documentation: `Result.scalar_one_or_none()`
- Аналогичный баг: N/A (первый случай)

