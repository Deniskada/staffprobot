# План исправления критических ошибок в payroll и добавление графика выплат в договоры

## 🎯 Цели
1. Исправить 2 критические ошибки в `core/celery/tasks/payroll_tasks.py`, чтобы начисления создавались автоматически через Celery
2. Добавить функционал выбора графика выплат в форме создания/редактирования договора с сотрудником

---

## 🔍 Проблемы

### Ошибка 1: Отсутствует импорт
**Строка 79:** `payment_period = await get_payment_period_for_date(schedule, today)`  
**Ошибка:** `NameError: name 'get_payment_period_for_date' is not defined`

### Ошибка 2: Необъявленная переменная
**Строка 431:** `total_entries_updated += 1`  
**Ошибка:** `NameError: name 'total_entries_updated' is not defined`

---

---

## 📋 ЧАСТЬ 1: Исправление ошибок в payroll_tasks.py

### Шаг 1: Анализ зависимостей
✅ **ВЫПОЛНЕНО** - Функция найдена в `shared/services/payment_schedule_service.py:9`

### Шаг 2: Проверка текущих импортов
✅ **ВЫПОЛНЕНО** - Уже импортируется `PayrollAdjustmentService` из `shared.services`

### Шаг 3: Внести изменения в код (DEV)

**Изменение 1 - Добавить импорт (после строки 20):**
```python
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from shared.services.payment_schedule_service import get_payment_period_for_date  # ← ДОБАВИТЬ
```

**Изменение 2 - Объявить переменную (строка 62):**
```python
total_entries_created = 0
total_entries_updated = 0  # ← ДОБАВИТЬ
total_adjustments_applied = 0
errors = []
```

**Изменение 3 - Обновить логирование (строка 462):**
```python
logger.info(
    f"Payroll entries creation completed",
    entries_created=total_entries_created,
    entries_updated=total_entries_updated,  # ← ДОБАВИТЬ
    adjustments_applied=total_adjustments_applied,
    errors_count=len(errors)
)
```

**Изменение 4 - Обновить return (строка 469):**
```python
return {
    'success': True,
    'date': today.isoformat(),
    'entries_created': total_entries_created,
    'entries_updated': total_entries_updated,  # ← ДОБАВИТЬ
    'adjustments_applied': total_adjustments_applied,
    'errors': errors
}
```

### Шаг 4: Проверка синтаксиса
```bash
python3 -m py_compile core/celery/tasks/payroll_tasks.py
```

### Шаг 5: Проверка линтера
Использовать `read_lints` в Cursor

### Шаг 6: Перезапуск контейнеров DEV
```bash
docker compose -f docker-compose.dev.yml restart celery_worker celery_beat
```

### Шаг 7: Тестирование на DEV
```bash
docker compose -f docker-compose.dev.yml exec web python << 'PYTHON'
from core.celery.tasks.payroll_tasks import create_payroll_entries_by_schedule
result = create_payroll_entries_by_schedule(target_date="2025-12-02")
print(f"Result: {result}")
PYTHON
```

### Шаг 8: Проверка логов DEV
```bash
docker compose -f docker-compose.dev.yml logs celery_worker --tail 100 | grep -A 20 "Starting payroll"
```

### Шаг 9: Проверка функции get_payment_period_for_date
```bash
docker compose -f docker-compose.dev.yml exec web python << 'PYTHON'
import asyncio
from datetime import date
from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.payment_schedule import PaymentSchedule
from shared.services.payment_schedule_service import get_payment_period_for_date

async def test():
    async with get_async_session() as session:
        result = await session.execute(
            select(PaymentSchedule).where(PaymentSchedule.id == 2)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            period = await get_payment_period_for_date(schedule, date(2025, 12, 2))
            print(f"Schedule ID={schedule.id}, Name={schedule.name}")
            print(f"Period: {period}")
        else:
            print("Schedule not found!")

asyncio.run(test())
PYTHON
```

### Шаг 10: Коммит изменений
```bash
git add core/celery/tasks/payroll_tasks.py
git commit -m "Исправление: добавлен импорт get_payment_period_for_date и переменная total_entries_updated"
```

### Шаг 11: Деплой на PROD
**ТОЛЬКО после успешного тестирования на DEV!**
```bash
git push origin main
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git pull && docker compose -f docker-compose.prod.yml restart celery_worker celery_beat'
```

### Шаг 12: Мониторинг PROD - payroll_tasks (3 декабря после 04:05)
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml logs celery_beat --since 2h | grep payroll'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod -c "SELECT COUNT(*), period_start, period_end, created_by_id FROM payroll_entries WHERE created_at >= NOW() - INTERVAL '\''24 hours'\'' GROUP BY period_start, period_end, created_by_id ORDER BY period_start DESC;"'
```

---

## 📋 ЧАСТЬ 2: График выплат в договорах

### Шаг 13: Анализ текущей структуры Contract
✅ **ВЫПОЛНЕНО** - `payment_schedule_id` уже существует в таблице `contracts`

**Текущее состояние:**
- Поле `payment_schedule_id` есть (nullable)
- Relationship к `PaymentSchedule` есть
- НО: в формах не отображается, нет логики наследования

### Шаг 14: Добавить чекбокс наследования в модель Contract

**Действие:** Создать миграцию Alembic для добавления поля `inherit_payment_schedule`

**Команды:**
```bash
cd /home/sa/projects/staffprobot
docker compose -f docker-compose.dev.yml exec web alembic revision -m "add_inherit_payment_schedule_to_contracts"
```

**Миграция (upgrade):**
```python
def upgrade():
    op.add_column('contracts', 
        sa.Column('inherit_payment_schedule', sa.Boolean(), 
                  nullable=False, server_default='true'))
```

**Миграция (downgrade):**
```python
def downgrade():
    op.drop_column('contracts', 'inherit_payment_schedule')
```

**Применить миграцию:**
```bash
docker compose -f docker-compose.dev.yml exec web alembic upgrade head
```

### Шаг 15: Обновить модель Contract

**Файл:** `domain/entities/contract.py`

**Добавить после строки 51:**
```python
payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
inherit_payment_schedule = Column(Boolean, default=True, nullable=False)  # ← ДОБАВИТЬ
```

### Шаг 16: Создать утилиту для получения наследуемого графика

**Файл:** `shared/services/contract_service.py` (или новый файл)

**Добавить функцию:**
```python
async def get_inherited_payment_schedule_id(
    contract: Contract,
    session: AsyncSession
) -> Optional[int]:
    """
    Получить ID графика выплат с учетом наследования от подразделения.
    
    Логика:
    1. Если inherit_payment_schedule=False → использовать contract.payment_schedule_id
    2. Если inherit_payment_schedule=True → найти график из подразделения первого объекта
    3. Поиск по цепочке: объект → подразделение → родительское подразделение → ...
    """
    if not contract.inherit_payment_schedule:
        return contract.payment_schedule_id
    
    # Получить первый объект из allowed_objects
    if not contract.allowed_objects or len(contract.allowed_objects) == 0:
        return None
    
    first_object_id = contract.allowed_objects[0]
    
    # Загрузить объект
    from domain.entities.object import Object
    result = await session.execute(
        select(Object).where(Object.id == first_object_id)
    )
    obj = result.scalar_one_or_none()
    
    if not obj or not obj.org_unit_id:
        return None
    
    # Получить график от подразделения (с учетом наследования)
    from domain.entities.org_structure import OrgStructureUnit
    result = await session.execute(
        select(OrgStructureUnit).where(OrgStructureUnit.id == obj.org_unit_id)
    )
    unit = result.scalar_one_or_none()
    
    if unit:
        return unit.get_inherited_payment_schedule_id()
    
    return None
```

### Шаг 17: Обновить форму создания договора

**Файл:** `apps/web/templates/owner/employees/create_contract.html`

**Добавить после блока с системой оплаты:**
```html
<!-- График выплат -->
<div class="row">
    <div class="col-md-12">
        <div class="mb-3">
            <div class="form-check mb-2">
                <input type="checkbox" 
                       class="form-check-input" 
                       id="inherit_payment_schedule" 
                       name="inherit_payment_schedule"
                       checked
                       onchange="togglePaymentScheduleInheritance()">
                <label class="form-check-label" for="inherit_payment_schedule">
                    Наследовать график выплат от подразделения
                </label>
            </div>
            
            <div id="payment_schedule_select_container">
                <label for="payment_schedule_id" class="form-label">График выплат</label>
                <select class="form-select" 
                        id="payment_schedule_id" 
                        name="payment_schedule_id"
                        disabled>
                    <option value="">Наследуется от подразделения</option>
                    {% for schedule in payment_schedules %}
                    <option value="{{ schedule.id }}">{{ schedule.name }}</option>
                    {% endfor %}
                </select>
                <small class="form-text text-muted">
                    График будет наследоваться от подразделения первого выбранного объекта
                </small>
            </div>
        </div>
    </div>
</div>

<script>
function togglePaymentScheduleInheritance() {
    const checkbox = document.getElementById('inherit_payment_schedule');
    const select = document.getElementById('payment_schedule_id');
    
    if (checkbox.checked) {
        select.disabled = true;
        select.value = '';
    } else {
        select.disabled = false;
    }
}

// Автоматически снимать чекбокс если выбрано >1 объекта
function updatePaymentScheduleInheritance() {
    const objectsCheckboxes = document.querySelectorAll('input[name="allowed_objects"]:checked');
    const inheritCheckbox = document.getElementById('inherit_payment_schedule');
    const scheduleSelect = document.getElementById('payment_schedule_id');
    
    if (objectsCheckboxes.length > 1) {
        // Более 1 объекта - снять чекбокс, выбрать график первого объекта
        inheritCheckbox.checked = false;
        scheduleSelect.disabled = false;
        
        // TODO: получить payment_schedule_id первого объекта и установить в select
        // Требует передачи данных об объектах с их графиками в шаблон
    }
}

// Вызывать при изменении выбора объектов
document.querySelectorAll('input[name="allowed_objects"]').forEach(checkbox => {
    checkbox.addEventListener('change', updatePaymentScheduleInheritance);
});
</script>
```

### Шаг 18: Обновить форму редактирования договора

**Файл:** `apps/web/templates/owner/employees/edit_contract.html`

**Добавить аналогичный блок с предзаполненными значениями:**
```html
<!-- График выплат -->
<div class="row">
    <div class="col-md-12">
        <div class="mb-3">
            <div class="form-check mb-2">
                <input type="checkbox" 
                       class="form-check-input" 
                       id="inherit_payment_schedule" 
                       name="inherit_payment_schedule"
                       {% if contract.inherit_payment_schedule %}checked{% endif %}
                       onchange="togglePaymentScheduleInheritance()">
                <label class="form-check-label" for="inherit_payment_schedule">
                    Наследовать график выплат от подразделения
                </label>
            </div>
            
            <div id="payment_schedule_select_container">
                <label for="payment_schedule_id" class="form-label">График выплат</label>
                <select class="form-select" 
                        id="payment_schedule_id" 
                        name="payment_schedule_id"
                        {% if contract.inherit_payment_schedule %}disabled{% endif %}>
                    <option value="">{% if contract.inherit_payment_schedule %}Наследуется от подразделения{% else %}Не выбран{% endif %}</option>
                    {% for schedule in payment_schedules %}
                    <option value="{{ schedule.id }}" 
                            {% if contract.payment_schedule_id == schedule.id %}selected{% endif %}>
                        {{ schedule.name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
        </div>
    </div>
</div>

<script>
function togglePaymentScheduleInheritance() {
    const checkbox = document.getElementById('inherit_payment_schedule');
    const select = document.getElementById('payment_schedule_id');
    const firstOption = select.querySelector('option[value=""]');
    
    if (checkbox.checked) {
        select.disabled = true;
        firstOption.textContent = 'Наследуется от подразделения';
        select.value = '';
    } else {
        select.disabled = false;
        firstOption.textContent = 'Не выбран';
    }
}
</script>
```

### Шаг 19: Обновить роуты создания договора

**Файл:** `apps/web/routes/owner.py` (функция `owner_employees_create_contract`)

**Добавить параметры:**
```python
payment_schedule_id: Optional[int] = Form(None),
inherit_payment_schedule: bool = Form(True),
```

**Передать в create_contract:**
```python
contract = await contract_service.create_contract(
    # ... существующие параметры ...
    payment_schedule_id=payment_schedule_id if not inherit_payment_schedule else None,
    inherit_payment_schedule=inherit_payment_schedule,
)
```

**Передать графики в шаблон (в GET route):**
```python
# Получить все графики владельца
payment_schedules = await session.execute(
    select(PaymentSchedule).where(
        PaymentSchedule.owner_id == user_id,
        PaymentSchedule.is_active == True
    )
)
payment_schedules = payment_schedules.scalars().all()

return templates.TemplateResponse(
    "owner/employees/create_contract.html",
    {
        # ... существующие параметры ...
        "payment_schedules": payment_schedules,
    }
)
```

### Шаг 20: Обновить роуты редактирования договора

**Аналогично шагу 19** для функций:
- `edit_contract_form` (GET) - передать `payment_schedules`
- `update_contract` (POST) - добавить параметры `payment_schedule_id`, `inherit_payment_schedule`

### Шаг 21: Обновить payroll_tasks.py - учет payment_schedule_id из контракта

**Файл:** `core/celery/tasks/payroll_tasks.py`

**После строки 203 (где contracts_result):**
```python
contracts = contracts_result.scalars().all()

logger.debug(f"Found {len(contracts)} contracts (active + terminated/schedule) for object {obj.id}")

for contract in contracts:
    try:
        # НОВАЯ ЛОГИКА: определить график выплат для контракта
        effective_payment_schedule_id = None
        
        if contract.inherit_payment_schedule:
            # Наследуем от подразделения
            from shared.services.contract_service import get_inherited_payment_schedule_id
            effective_payment_schedule_id = await get_inherited_payment_schedule_id(contract, session)
        else:
            # Используем явно указанный график
            effective_payment_schedule_id = contract.payment_schedule_id
        
        # Проверяем, совпадает ли график контракта с текущим графиком
        if effective_payment_schedule_id and effective_payment_schedule_id != schedule.id:
            logger.debug(
                f"Skip contract {contract.id}: different payment schedule",
                contract_schedule=effective_payment_schedule_id,
                current_schedule=schedule.id
            )
            continue
        
        # Если у контракта нет графика (ни явного, ни наследуемого) - используем график объекта
        if not effective_payment_schedule_id:
            logger.debug(
                f"Contract {contract.id} has no payment schedule, using object schedule {schedule.id}"
            )
        
        # Продолжаем существующую логику создания начислений...
```

### Шаг 22: Тестирование на DEV - формы договоров

**Команды:**
```bash
# Перезапуск web
docker compose -f docker-compose.dev.yml restart web

# Открыть форму создания договора
# http://localhost:8001/owner/employees/create

# Проверить:
# 1. Чекбокс "Наследовать график выплат" включен по умолчанию
# 2. Дропдаун disabled, показывает "Наследуется от подразделения"
# 3. При снятии чекбокса - дропдаун активируется, показывает список графиков
# 4. При выборе >1 объекта - чекбокс автоматически снимается
```

### Шаг 23: Тестирование на DEV - логика наследования

**Команды:**
```bash
docker compose -f docker-compose.dev.yml exec web python << 'PYTHON'
import asyncio
from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.contract import Contract
from shared.services.contract_service import get_inherited_payment_schedule_id

async def test():
    async with get_async_session() as session:
        # Получить тестовый контракт
        result = await session.execute(
            select(Contract).where(Contract.id == 63)
        )
        contract = result.scalar_one_or_none()
        
        if contract:
            print(f"Contract ID={contract.id}")
            print(f"inherit_payment_schedule={contract.inherit_payment_schedule}")
            print(f"payment_schedule_id={contract.payment_schedule_id}")
            
            # Получить наследуемый график
            inherited_id = await get_inherited_payment_schedule_id(contract, session)
            print(f"Inherited payment_schedule_id={inherited_id}")
        else:
            print("Contract not found!")

asyncio.run(test())
PYTHON
```

### Шаг 24: Применить миграцию на PROD

**ТОЛЬКО после успешного тестирования на DEV!**

```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic upgrade head'
```

### Шаг 25: Мониторинг PROD - формы договоров

**Проверить:**
1. Формы создания/редактирования договоров работают корректно
2. Чекбокс и дропдаун ведут себя правильно
3. Существующие договоры не сломались
4. Начисления создаются с учетом графика контракта

---

## ⚠️ Риски и меры предосторожности

### Риск 1: Неправильный расчет периодов
**Митигация:** Протестировать на DEV с реальными данными

### Риск 2: Дублирование начислений
**Митигация:** В коде есть проверка `existing_entry_query` (строка 212-219)

### Риск 3: Ошибки в логике обновления
**Митигация:** Мы только добавляем переменную, не меняем бизнес-логику

### Риск 4: Несоответствие с ручными начислениями
**Митигация:** Автоматические с `created_by_id=NULL`, ручные с `created_by_id!=NULL`

### Риск 5: Существующие договоры без графика выплат
**Митигация:** 
- Поле `inherit_payment_schedule` с default=True
- Если нет графика в контракте и подразделении - используется график объекта

### Риск 6: Логика выбора графика при >1 объекте
**Митигация:**
- JS автоматически снимает чекбокс
- Требует явного выбора графика пользователем
- Лог-предупреждение если графики объектов различаются

---

## 📊 Критерии успеха

### DEV тестирование
- ✅ Код компилируется без ошибок
- ✅ Линтер не показывает критических ошибок
- ✅ Задача запускается вручную без ошибок
- ✅ Функция `get_payment_period_for_date` работает корректно
- ✅ Периоды рассчитываются правильно: 2.12.2025 → 10.11-16.11
- ✅ Логи содержат `entries_created` и `entries_updated`

### PROD мониторинг
- ✅ Задача запускается по расписанию (04:00 МСК)
- ✅ В логах нет ошибок `NameError`
- ✅ Начисления создаются с `created_by_id=NULL`
- ✅ Периоды соответствуют графикам

### Договоры - тестирование
- ✅ Миграция применена без ошибок
- ✅ Чекбокс "Наследовать график" работает
- ✅ Дропдаун корректно disable/enable
- ✅ При >1 объекте чекбокс снимается автоматически
- ✅ Форма редактирования показывает сохраненные значения
- ✅ Логика наследования работает корректно
- ✅ Начисления учитывают график контракта

---

## 🔄 Откат (если что-то пойдет не так)

```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git log --oneline -5'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git reset --hard <PREVIOUS_COMMIT>'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml restart celery_worker celery_beat'
```

**Важно:** После отката начисления придется создавать вручную!

---

## 📝 Обновление документации

После успешного деплоя:

1. `doc/plans/roadmap.md` - добавить Итерацию 50
2. `doc/ANALYSIS_PAYROLL_BUG.md` - создать детальный анализ
3. Коммит документации

---

## ⏱️ Время выполнения

### Часть 1: Payroll tasks
- Подготовка и изменения: ~10 минут
- Тестирование на DEV: ~15 минут
- Коммит и деплой: ~5 минут
- Мониторинг (следующий день): ~5 минут

**Итого Часть 1:** ~35 минут + мониторинг

### Часть 2: График выплат в договорах
- Миграция БД: ~5 минут
- Обновление модели: ~5 минут
- Создание утилиты наследования: ~15 минут
- Обновление форм (шаблоны): ~20 минут
- Обновление роутов: ~15 минут
- Обновление payroll_tasks логики: ~10 минут
- Тестирование на DEV: ~20 минут
- Коммит и деплой: ~5 минут

**Итого Часть 2:** ~95 минут (~1.5 часа)

**ОБЩЕЕ ВРЕМЯ:** ~2 часа + мониторинг на следующий день

---

## ✅ Чеклист перед деплоем

### Часть 1: Payroll tasks
- [ ] Импорт `get_payment_period_for_date` добавлен
- [ ] Переменная `total_entries_updated` объявлена
- [ ] Логи и return обновлены
- [ ] Код компилируется
- [ ] Линтер OK
- [ ] DEV тестирование OK
- [ ] Функция работает корректно
- [ ] Периоды рассчитываются правильно

### Часть 2: График выплат в договорах
- [ ] Миграция создана и применена на DEV
- [ ] Поле `inherit_payment_schedule` добавлено в Contract
- [ ] Функция `get_inherited_payment_schedule_id` реализована
- [ ] Формы создания/редактирования обновлены
- [ ] JavaScript логика работает
- [ ] Роуты GET/POST обновлены
- [ ] payroll_tasks учитывает график контракта
- [ ] Тестирование на DEV пройдено
- [ ] Миграция применена на PROD

### Общее
- [ ] Все коммиты созданы
- [ ] Документация обновлена
- [ ] План отката готов

