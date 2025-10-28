# Отчёт по исправлению начислений (28.10.2025)

## Корневые причины проблемы

### 1. **Владелец 1220971779 (Голикова и др.)**
**Причина**: Фильтр `Contract.is_active == True` в "Пересчитать вручную"

**Детали**:
- Голикова и др. имеют `status='terminated', is_active=False, settlement_policy='schedule'`
- Код **УЖЕ УЧИТЫВАЛ** `settlement_policy='schedule'` ✅
- НО **ТАКЖЕ фильтровал** `is_active == True` для активных ❌
- **Результат**: terminated-сотрудники не попадали в пересчёт

**Исправление**: Убран `is_active` из `or_(...)` — теперь ВСЕ `status='active'` учитываются

### 2. **Владелец 1170536174 (Дарья и др.)**
**Причина**: НЕТ начислений вообще (включая активных сотрудников)

**Детали**:
- График #5 (monthly, 25-е число) **отработал** 25.10 в 01:00
- Нашёл объект #8, 4 контракта (включая Дарью)
- **НО** `get_unapplied_adjustments` вернул **пустой список** для всех 4!
- **SQL-запрос** находит корректировки ✅, но **Python-код** — нет ❌

**Гипотеза**: На проде **старая версия** кода (образы Celery 3 недели назад), где:
- `get_unapplied_adjustments` фильтрует по `created_at` вместо `Shift.end_time`
- Корректировки Дарьи: `created_at` 12-28.10, но период 26.08-25.09 → **не попали**!

**Исправление**: Пересборка образов Celery (актуальный код с фильтром по `Shift.end_time`)

---

## Применённые исправления (прод)

### ✅ **Изменение 1**: `apps/web/routes/payroll.py` (строка 609)
**Старый код**:
```python
or_(
    and_(Contract.status == 'active', Contract.is_active == True),  # ❌
    and_(Contract.status == 'terminated', Contract.settlement_policy == 'schedule')
)
```

**Новый код**:
```python
or_(
    Contract.status == 'active',  # Все активные (независимо от is_active)
    and_(Contract.status == 'terminated', Contract.settlement_policy == 'schedule')
)
```

### ✅ **Изменение 2**: `apps/web/routes/owner_payroll_adjustments.py` (строки 84-92, 189-191)
**Старый код** (2 места):
```python
# Место 1: employee_ids для фильтра корректировок
employee_ids_query = select(Contract.employee_id).where(
    Contract.owner_id == owner_id,
    Contract.is_active == True,  # ❌
    Contract.status == 'active'  # ❌
)

# Место 2: список сотрудников для выпадающего списка
employees_query = select(User).join(Contract, ...).where(
    Contract.owner_id == owner_id,
    Contract.is_active == True,  # ❌
    Contract.status == 'active'  # ❌
)
```

**Новый код**:
```python
# Место 1
employee_ids_query = select(Contract.employee_id).where(
    Contract.owner_id == owner_id  # Показываем всех
)

# Место 2
employees_query = select(User).join(Contract, ...).where(
    Contract.owner_id == owner_id  # Показываем всех
)
```

### ✅ **Изменение 3**: `apps/web/routes/manager_payroll_adjustments.py` (строки 147-150)
**Аналогично** owner — убраны фильтры `is_active` и `status`

### ✅ **Изменение 4**: Пересборка Celery worker + beat
```bash
docker compose -f docker-compose.prod.yml down celery_worker celery_beat
docker compose -f docker-compose.prod.yml up -d celery_worker celery_beat web
```

**Результат**: Актуальный код `get_unapplied_adjustments` с фильтром по `Shift.end_time`

---

## Результаты тестирования

### До исправлений (28.10, 01:00 UTC)
**Владелец 1220971779**:
- ✅ 23 начисления создано (график #2, вторник)
- ❌ Но ТОЛЬКО для активных с `is_active=True`
- ❌ Голикова и др. (11 сотрудников) **НЕ ПОЛУЧИЛИ** начисления

**Владелец 1170536174**:
- Celery: "Found 4 contracts, No adjustments for employee" (4 раза)
- ❌ **0 начислений** создано (хотя есть 8 корректировок у Дарьи)

### После исправлений (тестирование)
**Ожидаемый результат** после "Пересчитать вручную" (дата 25.10):
- ✅ Создадутся начисления для Дарьи, Эвелины (если есть корректировки)
- ✅ Период: 26.08-25.09 (график #5, payment_num=1)

**Проверка**: `SELECT COUNT(*) FROM payroll_entries WHERE employee_id IN (14,16,17,60) AND period_start='2025-08-26'`

---

## Дополнительные улучшения (опционально)

### 1. Логирование employee_id в Celery
**Файл**: `core/celery/tasks/payroll_tasks.py:174`

**Добавить**:
```python
logger.debug(
    f"No adjustments for employee",
    employee_id=contract.employee_id,
    contract_id=contract.id,
    period_start=period_start,
    period_end=period_end
)
```

### 2. Мониторинг Celery задач
**Метрики**:
- `payroll_entries_created_total{owner_id, schedule_id}`
- `payroll_contracts_processed{owner_id, object_id}`
- Алерт: если график сработал, но `entries_created=0`

### 3. UI улучшения
- Показывать статус договора (`active`/`terminated`) рядом с именем сотрудника
- Фильтр "Показывать только активных" — checkbox (по умолчанию OFF)

---

## Чек-лист проверки после деплоя

- [ ] `/owner/payroll/adjustments` — в списке сотрудников появились уволенные
- [ ] "Пересчитать вручную" (25.10) → созданы начисления для владельца 1170536174
- [ ] "Пересчитать вручную" (28.10) → обновлены начисления для владельца 1220971779 (включая Голикову)
- [ ] Завтра (29.10, вторник) → Celery автоматически создаст начисления за 13-19.10
- [ ] Можно создавать ручные корректировки для уволенных сотрудников
- [ ] Логи Celery: нет "No adjustments" для сотрудников с корректировками

---

## Статус

- [x] Анализ завершён (`doc/PAYROLL_ANALYSIS_20251028.md`)
- [x] Исправления применены на проде (sed, без коммита в main)
- [x] Celery пересобран и перезапущен
- [x] Web перезапущен
- [ ] **ОЖИДАНИЕ**: Пользователь тестирует "Пересчитать вручную" (25.10)
- [ ] Проверка результатов
- [ ] Коммит в hotfix-ветку + merge в main

**Последнее обновление**: 28.10.2025, 17:42 MSK

