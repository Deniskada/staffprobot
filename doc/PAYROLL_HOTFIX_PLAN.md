# План исправления начислений уволенным сотрудникам

**Дата**: 28.10.2025  
**Ветка**: `hotfix/payroll-terminated-contracts`  
**Критичность**: ВЫСОКАЯ (сотрудники не получили зарплату за 2 недели!)

---

## Корневая причина

**График выплат #2** (Еженедельно, по вторникам) настроен **НЕПРАВИЛЬНО**:
- `start_offset = -22` (3 недели назад)
- `end_offset = -16` (2+ недели назад)

**Результат**: Каждый вторник создаются **дубликаты** начислений за период **06-12.10**, а периоды **13-19** и **20-26** октября **пропускаются**.

---

## План исправлений (3 этапа)

### Этап 1: НЕМЕДЛЕННО — Исправить график выплат (5 мин)

#### Действие 1.1: UPDATE графика #2 на проде
```sql
UPDATE payment_schedules 
SET payment_period = jsonb_set(
    jsonb_set(
        payment_period::jsonb,
        '{start_offset}', '-7'
    ),
    '{end_offset}', '-1'
),
updated_at = NOW()
WHERE id = 2;
```

**Команда**:
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod' << 'EOF'
UPDATE payment_schedules 
SET payment_period = jsonb_set(
    jsonb_set(
        payment_period::jsonb,
        '{start_offset}', '-7'
    ),
    '{end_offset}', '-1'
),
updated_at = NOW()
WHERE id = 2;

SELECT id, name, payment_period FROM payment_schedules WHERE id = 2;
EOF
```

**Результат**: Завтра (29.10, вторник) создадутся начисления за **22-28.10** ✅

---

### Этап 2: СРОЧНО — Backfill пропущенных начислений (30 мин)

#### Действие 2.1: Создать скрипт backfill

**Файл**: `scripts/backfill_payroll_20251028.py`

**Логика**:
1. Найти 6 сотрудников (Голикова, Магера, Лобачева, Николенко, Кравченков, Семенюк)
2. Для каждого:
   - Период 1: `2025-10-13 → 2025-10-19` (вторник 20.10)
   - Период 2: `2025-10-20 → 2025-10-26` (вторник 27.10, но был понедельник — **пропущен!**)
3. Найти неприменённые `PayrollAdjustment` за эти периоды
4. Создать `PayrollEntry` (аналогично `payroll_tasks.py:142-280`)
5. Отметить корректировки как применённые

**Псевдокод**:
```python
async def backfill():
    user_ids = [40, 33, 32, 34, 44, 47]  # Голикова и др.
    periods = [
        (date(2025, 10, 13), date(2025, 10, 19)),
        (date(2025, 10, 20), date(2025, 10, 26))
    ]
    
    for user_id in user_ids:
        contract = await get_latest_contract(user_id)  # terminated + settlement_policy='schedule'
        for period_start, period_end in periods:
            adjustments = await get_unapplied_adjustments(user_id, period_start, period_end)
            if adjustments:
                # Создать PayrollEntry (логика из payroll_tasks.py)
                # ...
```

#### Действие 2.2: Запустить скрипт на проде
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web python scripts/backfill_payroll_20251028.py'
```

**Результат**: Созданы начисления за 13-19 и 20-26 октября для 6 сотрудников ✅

---

### Этап 3: Убрать фильтр `is_active=True` (30 мин)

#### Действие 3.1: Изменить `owner_payroll_adjustments.py`

**Файл**: `apps/web/routes/owner_payroll_adjustments.py:185-193`

**Старый код**:
```python
employees_query = select(User).join(
    Contract, Contract.employee_id == User.id
).where(
    Contract.owner_id == owner_id,
    Contract.is_active == True,  # ❌ УБРАТЬ
    Contract.status == 'active'  # ❌ УБРАТЬ
).distinct().order_by(User.last_name, User.first_name)
```

**Новый код**:
```python
employees_query = select(User).join(
    Contract, Contract.employee_id == User.id
).where(
    Contract.owner_id == owner_id
    # Показываем ВСЕХ сотрудников (включая уволенных)
).distinct().order_by(User.last_name, User.first_name)
```

**Обоснование**: Owner должен видеть ВСЕХ когда-либо работавших сотрудников для создания ручных корректировок задним числом.

#### Действие 3.2: Аналогично для manager

**Файл**: `apps/web/routes/manager_payroll_adjustments.py:144-151`

**Изменить**:
```python
employees_query = select(User).join(
    Contract, Contract.employee_id == User.id
).where(
    # Убрать фильтры is_active и status
)
```

#### Действие 3.3: Тестирование
1. **Dev**: Создать корректировку для уволенного → должен появиться в списке
2. **Prod**: Деплой после проверки на dev

---

## Среднесрочные улучшения (опционально)

### 1. Валидация offset при создании графика

**Файл**: `apps/web/routes/payment_schedule.py` (роут создания графика)

**Добавить проверку**:
```python
if frequency == 'weekly':
    if start_offset > -7 or start_offset < -14:
        raise ValueError("Для еженедельного графика start_offset должен быть от -14 до -7")
    if end_offset > -1 or end_offset < -7:
        raise ValueError("Для еженедельного графика end_offset должен быть от -7 до -1")
```

### 2. UI подсказки

**Файл**: `apps/web/templates/owner/payment_schedule/create.html`

**Добавить**:
```html
<small class="form-text text-muted">
  <strong>Рекомендуемые значения:</strong><br>
  • Еженедельно: начало -7, конец -1 (прошлая неделя)<br>
  • Раз в 2 недели: начало -14, конец -1<br>
  • Ежемесячно: зависит от числа выплат
</small>
```

### 3. Расширить "Пересчитать вручную"

**Добавить поля**:
- `period_start` (date) — начало периода
- `period_end` (date) — конец периода
- `include_terminated` (checkbox) — включить уволенных

**Логика**: Если указаны `period_start/end` → использовать их, иначе — рассчитывать по графику.

---

## Критика плана (второй проход)

### Что может пойти не так?

1. **Дубли при backfill**:
   - **Риск**: Создадутся дубликаты начислений за 06-12.10
   - **Защита**: Проверка `existing_entry_query` (уже есть в `payroll_tasks.py:643-650`)

2. **Корректировки вне периода**:
   - **Риск**: У Руднева, Дремовой корректировки могут быть за **другие** периоды
   - **Защита**: Логировать `adjustments.created_at` и фильтровать по датам смен

3. **Объекты не используют график #2**:
   - **Риск**: Объекты [1], [4] могут использовать **другой график** (не #2)
   - **Защита**: Проверить `objects.payment_schedule_id` для этих объектов

4. **Убрать фильтр is_active → слишком много сотрудников**:
   - **Риск**: Список сотрудников на `/owner/payroll/adjustments` станет огромным
   - **Защита**: Добавить фильтр "Показывать только активных" (checkbox, по умолчанию включён)

### Уточнённый план Этапа 3

**Изменить логику фильтра**:
```python
# По умолчанию показываем только активных
show_all = request.query_params.get('show_all_employees', 'false') == 'true'

employees_query = select(User).join(
    Contract, Contract.employee_id == User.id
).where(
    Contract.owner_id == owner_id
)

if not show_all:
    employees_query = employees_query.where(
        Contract.is_active == True,
        Contract.status == 'active'
    )

employees_query = employees_query.distinct().order_by(User.last_name, User.first_name)
```

**UI**: Добавить checkbox "Показать всех сотрудников (включая уволенных)"

---

## Итоговый чек-лист (обновлённый)

### ⚡ **НЕМЕДЛЕННО**
- [ ] UPDATE график #2 на проде (`start_offset=-7, end_offset=-1`)
- [ ] Проверить завтра (29.10) — создадутся ли начисления за 22-28.10

### 🔥 **СРОЧНО** (после согласования пользователя)
- [ ] Backfill скрипт: начисления за 13-19 и 20-26 октября
- [ ] Убрать фильтр `is_active` с checkbox "Показать всех" (owner + manager)
- [ ] Тест на dev → деплой на прод

### 📅 **ОПЦИОНАЛЬНО**
- [ ] Валидация offset при создании графика
- [ ] UI подсказки для offset
- [ ] Расширить "Пересчитать вручную" (произвольный период)

---

## Вопросы к пользователю (для финализации плана)

1. **Backfill скрипт**: 
   - Запустить сразу после UPDATE графика?
   - Или дождаться 29.10 (проверить, что график работает) и потом backfill?

2. **Фильтр "Показать всех"**: 
   - По умолчанию включён (показывать только активных)?
   - Или по умолчанию выключен (показывать всех)?

3. **Деплой на прод**: 
   - Сразу после UPDATE графика + backfill?
   - Или протестировать на dev → потом на прод?

