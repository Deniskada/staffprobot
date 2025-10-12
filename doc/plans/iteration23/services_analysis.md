# Анализ middleware и сервисов для Итерации 23

**Дата:** 2025-10-09  
**Статус:** Завершен  
**Задача:** 0.5. Анализ middleware и сервисов

## Оглавление

1. [Новые сервисы](#1-новые-сервисы)
2. [Изменения в существующих сервисах](#2-изменения-в-существующих-сервисах)
3. [Новые middleware/зависимости](#3-новые-middlewareзависимости)
4. [Celery задачи](#4-celery-задачи)
5. [Итоговая статистика](#5-итоговая-статистика)

---

## 1. Новые сервисы

### 1.1. PaymentSystemService

**Файл:** `apps/web/services/payment_system_service.py` (СОЗДАТЬ)

**Назначение:** Управление справочником систем оплаты труда

**Методы:**
```python
class PaymentSystemService(BaseService):
    """Сервис для работы с системами оплаты труда."""
    
    async def get_all_systems(self) -> List[PaymentSystem]:
        """Получить все системы оплаты."""
    
    async def get_active_systems(self) -> List[PaymentSystem]:
        """Получить активные системы оплаты."""
    
    async def get_system_by_id(self, system_id: int) -> Optional[PaymentSystem]:
        """Получить систему по ID."""
    
    async def get_system_by_code(self, code: str) -> Optional[PaymentSystem]:
        """Получить систему по коду (simple_hourly, salary, etc)."""
    
    async def calculate_payment(
        self, 
        system_code: str, 
        hours: float, 
        base_rate: float,
        bonuses: List[Dict] = None,
        deductions: List[Dict] = None
    ) -> float:
        """
        Рассчитать выплату по системе оплаты.
        
        Args:
            system_code: Код системы оплаты
            hours: Количество часов
            base_rate: Базовая ставка
            bonuses: Список доплат
            deductions: Список удержаний
            
        Returns:
            Сумма к выплате
        """
```

**Зависимости:** BaseService, PaymentSystem model

**Тесты:** `tests/unit/test_payment_system_service.py`

---

### 1.2. PayrollService

**Файл:** `apps/web/services/payroll_service.py` (СОЗДАТЬ)

**Назначение:** Управление начислениями, удержаниями и выплатами

**Методы:**
```python
class PayrollService(BaseService):
    """Сервис для работы с начислениями и выплатами."""
    
    async def calculate_payroll(
        self, 
        employee_id: int,
        period_start: date,
        period_end: date
    ) -> PayrollEntry:
        """
        Рассчитать начисление за период.
        
        1. Получить все смены сотрудника за период
        2. Рассчитать базовую оплату (часы * ставки)
        3. Получить автоматические удержания
        4. Получить ручные удержания и доплаты
        5. Рассчитать итоговую сумму
        """
    
    async def create_payroll_entry(self, data: Dict) -> PayrollEntry:
        """Создать начисление."""
    
    async def approve_payroll(self, entry_id: int, approved_by: int) -> PayrollEntry:
        """Одобрить начисление (draft → approved)."""
    
    async def add_deduction(
        self,
        payroll_entry_id: int,
        amount: float,
        description: str,
        is_automatic: bool = False,
        shift_id: Optional[int] = None,
        created_by: int
    ) -> PayrollDeduction:
        """Добавить удержание."""
    
    async def add_bonus(
        self,
        payroll_entry_id: int,
        amount: float,
        description: str,
        shift_id: Optional[int] = None,
        created_by: int
    ) -> PayrollBonus:
        """Добавить доплату."""
    
    async def record_payment(
        self,
        payroll_entry_id: int,
        payment_date: date,
        amount: float,
        payment_method: str,
        notes: Optional[str] = None
    ) -> EmployeePayment:
        """
        Записать факт выплаты (approved → paid).
        
        Args:
            payment_method: 'card', 'cash', 'bank'
        """
    
    async def get_employee_payroll_history(
        self,
        employee_id: int,
        limit: int = 10
    ) -> List[PayrollEntry]:
        """Получить историю выплат сотрудника."""
    
    async def get_upcoming_payments(
        self,
        owner_id: int,
        schedule_id: Optional[int] = None
    ) -> List[Dict]:
        """Получить предстоящие выплаты по графику."""
    
    async def get_payroll_by_id(self, entry_id: int) -> Optional[PayrollEntry]:
        """Получить начисление по ID с детализацией."""
```

**Зависимости:** 
- BaseService
- PayrollEntry, PayrollDeduction, PayrollBonus, EmployeePayment models
- Shift model
- PaymentSystemService

**Тесты:** 
- `tests/unit/test_payroll_service.py`
- `tests/integration/test_payroll_flow.py`

---

### 1.3. OrgStructureService

**Файл:** `apps/web/services/org_structure_service.py` (СОЗДАТЬ)

**Назначение:** Управление организационной структурой

**Методы:**
```python
class OrgStructureService(BaseService):
    """Сервис для работы с организационной структурой."""
    
    async def get_org_tree(self, owner_id: int) -> List[Dict]:
        """Получить дерево подразделений владельца."""
    
    async def get_unit_by_id(self, unit_id: int) -> Optional[OrgStructureUnit]:
        """Получить подразделение по ID."""
    
    async def create_unit(
        self,
        owner_id: int,
        name: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None,
        payment_system_id: Optional[int] = None,
        payment_schedule_id: Optional[int] = None
    ) -> OrgStructureUnit:
        """
        Создать подразделение.
        
        Валидация:
        - Проверка на циклические ссылки
        - Рассчитать level из parent
        """
    
    async def update_unit(self, unit_id: int, data: Dict) -> OrgStructureUnit:
        """Обновить подразделение."""
    
    async def move_unit(self, unit_id: int, new_parent_id: Optional[int]) -> OrgStructureUnit:
        """
        Переместить подразделение.
        
        Валидация:
        - Запрет перемещения в собственного потомка
        - Пересчитать level для всего поддерева
        """
    
    async def delete_unit(self, unit_id: int) -> bool:
        """
        Удалить подразделение.
        
        Проверки:
        - Нет дочерних подразделений
        - Нет привязанных объектов
        """
    
    async def get_inherited_payment_system(self, unit_id: int) -> Optional[PaymentSystem]:
        """Получить систему оплаты с учетом наследования."""
    
    async def get_inherited_payment_schedule(self, unit_id: int) -> Optional[PaymentSchedule]:
        """Получить график выплат с учетом наследования."""
    
    async def get_objects_for_unit(
        self, 
        unit_id: int, 
        include_children: bool = True
    ) -> List[Object]:
        """Получить объекты подразделения (и дочерних, если include_children=True)."""
    
    async def validate_no_circular_reference(
        self, 
        unit_id: int, 
        new_parent_id: int
    ) -> bool:
        """Проверить отсутствие циклических ссылок."""
```

**Зависимости:**
- BaseService
- OrgStructureUnit, PaymentSystem, PaymentSchedule, Object models

**Тесты:**
- `tests/unit/test_org_structure_service.py`
- `tests/integration/test_org_inheritance.py`

---

### 1.4. ShiftTaskService

**Файл:** `apps/web/services/shift_task_service.py` (СОЗДАТЬ)

**Назначение:** Управление задачами на смене

**Методы:**
```python
class ShiftTaskService(BaseService):
    """Сервис для работы с задачами на смене."""
    
    async def get_tasks_for_object(self, object_id: int) -> List[Dict]:
        """
        Получить задачи объекта по умолчанию.
        
        Returns:
            [{task: str, is_mandatory: bool, deduction_amount: float}, ...]
        """
    
    async def get_tasks_for_timeslot(self, timeslot_id: int) -> List[TimeslotTaskTemplate]:
        """Получить задачи тайм-слота (переопределяют объект)."""
    
    async def create_shift_tasks(
        self, 
        shift_id: int, 
        tasks: List[Dict]
    ) -> List[ShiftTask]:
        """
        Создать задачи при открытии смены.
        
        Args:
            tasks: Список задач из тайм-слота или объекта
        """
    
    async def complete_task(self, task_id: int, completed_at: datetime) -> ShiftTask:
        """Отметить задачу как выполненную."""
    
    async def check_incomplete_tasks(self, shift_id: int) -> List[ShiftTask]:
        """Проверить невыполненные обязательные задачи при закрытии смены."""
    
    async def get_tasks_for_shift(self, shift_id: int) -> List[ShiftTask]:
        """Получить все задачи смены."""
    
    async def save_timeslot_tasks(
        self,
        timeslot_id: int,
        tasks: List[Dict]
    ) -> List[TimeslotTaskTemplate]:
        """Сохранить шаблоны задач для тайм-слота."""
```

**Зависимости:**
- BaseService
- ShiftTask, TimeslotTaskTemplate, Object, TimeSlot models

**Тесты:**
- `tests/unit/test_shift_task_service.py`

---

## 2. Изменения в существующих сервисах

### 2.1. ContractService

**Файл:** `apps/web/services/contract_service.py` (ИЗМЕНИТЬ)

**Новые/измененные методы:**

```python
class ContractService:
    # ... существующие методы ...
    
    async def create_contract(self, data: Dict) -> Contract:
        """
        Создать договор.
        
        ИЗМЕНЕНИЯ:
        - Добавить обработку use_contract_rate
        - Добавить payment_system_id (default: simple_hourly)
        - Добавить payment_schedule_id
        - Валидация: если use_contract_rate=True, hourly_rate обязателен
        - Преобразование hourly_rate: копейки → рубли (после миграции)
        """
    
    async def update_contract(self, contract_id: int, data: Dict) -> Contract:
        """
        Обновить договор.
        
        ИЗМЕНЕНИЯ:
        - Обработка новых полей
        - Валидация use_contract_rate + hourly_rate
        """
    
    async def get_effective_hourly_rate(
        self, 
        contract: Contract, 
        shift_obj: Object,
        timeslot: Optional[TimeSlot] = None
    ) -> float:
        """
        Определить применяемую ставку (НОВЫЙ МЕТОД).
        
        Приоритет:
        1. contract.hourly_rate (если use_contract_rate=True)
        2. timeslot.hourly_rate (если есть)
        3. shift_obj.hourly_rate (fallback)
        
        Returns:
            Ставка в рублях
        """
```

**Тесты:**
- Обновить `tests/unit/test_contract_service.py`
- Добавить тесты для `get_effective_hourly_rate()`

---

### 2.2. ObjectService

**Файл:** `apps/web/services/object_service.py` (ИЗМЕНИТЬ)

**Новые/измененные методы:**

```python
class ObjectService:
    # ... существующие методы ...
    
    async def create_object(self, data: Dict) -> Object:
        """
        Создать объект.
        
        ИЗМЕНЕНИЯ:
        - Добавить org_unit_id (default: "Основное подразделение")
        - Добавить payment_system_id (nullable, наследуется от org_unit)
        - Добавить payment_schedule_id (nullable)
        - Обработка shift_tasks в новом формате [{task, is_mandatory, deduction_amount}]
        - Валидация структуры shift_tasks через Pydantic
        """
    
    async def update_object(self, object_id: int, data: Dict) -> Object:
        """
        Обновить объект.
        
        ИЗМЕНЕНИЯ:
        - Обработка новых полей
        - Валидация shift_tasks
        """
    
    async def get_effective_payment_system(self, object_id: int) -> Optional[PaymentSystem]:
        """
        Получить эффективную систему оплаты (НОВЫЙ МЕТОД).
        
        Приоритет:
        1. object.payment_system_id (если указан)
        2. object.org_unit.payment_system_id (наследование)
        """
    
    async def get_objects_for_org_unit(
        self, 
        org_unit_id: int, 
        include_children: bool = True
    ) -> List[Object]:
        """
        Получить объекты подразделения (НОВЫЙ МЕТОД).
        
        Args:
            include_children: Включать объекты дочерних подразделений
        """
```

**Тесты:**
- Обновить `tests/unit/test_object_service.py`
- Добавить тесты для наследования настроек

---

### 2.3. ShiftService (shared)

**Файл:** `shared/services/shift_service.py` (ИЗМЕНИТЬ)

**Новые/измененные методы:**

```python
class ShiftService(BaseService):
    # ... существующие методы ...
    
    async def open_shift(self, user_id: int, object_id: int, coordinates: str) -> Dict:
        """
        Открыть смену.
        
        ИЗМЕНЕНИЯ:
        - Использовать ContractService.get_effective_hourly_rate()
        - Создать задачи смены через ShiftTaskService
        - Логирование источника ставки
        """
    
    async def close_shift(self, user_id: int, coordinates: str) -> Dict:
        """
        Закрыть смену.
        
        ИЗМЕНЕНИЯ:
        - Проверить невыполненные обязательные задачи через ShiftTaskService
        - Сохранить информацию о невыполненных задачах
        - Расчет выплаты с учетом новой логики
        """
    
    async def determine_hourly_rate(
        self,
        user_id: int,
        object_id: int,
        timeslot_id: Optional[int] = None
    ) -> Tuple[float, str]:
        """
        Централизованное определение ставки (НОВЫЙ МЕТОД).
        
        Returns:
            (hourly_rate, source) где source: 'contract', 'timeslot', 'object'
        """
```

**Зависимости:**
- Добавить ContractService
- Добавить ShiftTaskService

**Тесты:**
- Обновить `tests/unit/test_shift_service.py`
- Добавить `tests/integration/test_shift_rate_priority.py`

---

## 3. Новые middleware/зависимости

### 3.1. Зависимость для прав управляющего на начисления

**Файл:** `apps/web/dependencies.py` (ИЗМЕНИТЬ)

**Добавить:**

```python
async def require_manager_payroll_permission(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """
    Проверка права управляющего на работу с начислениями.
    
    Требования:
    1. Пользователь авторизован
    2. Имеет роль manager (или owner/superadmin)
    3. В активном договоре с is_manager=True и manager_permissions.can_manage_payroll=True
    """
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    # Owner и superadmin имеют доступ по умолчанию
    if current_user.role in ['owner', 'superadmin']:
        return current_user
    
    # Для manager проверить права
    if current_user.role == 'manager':
        # Получить активные договоры управляющего
        async with get_async_session() as session:
            query = select(Contract).where(
                Contract.employee_id == current_user.id,
                Contract.is_manager == True,
                Contract.status == 'active'
            )
            result = await session.execute(query)
            contracts = result.scalars().all()
            
            # Проверить наличие права can_manage_payroll
            for contract in contracts:
                permissions = contract.manager_permissions or {}
                if permissions.get('can_manage_payroll', False):
                    return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для работы с начислениями"
    )
```

---

### 3.2. Зависимость для доступа к начислениям по объектам

**Файл:** `apps/web/dependencies.py` (ИЗМЕНИТЬ)

**Добавить:**

```python
async def check_payroll_access(
    payroll_entry_id: int,
    current_user: User = Depends(require_manager_payroll_permission)
) -> PayrollEntry:
    """
    Проверка доступа к начислению.
    
    Для owner: доступ ко всем начислениям своих сотрудников
    Для manager: доступ только к начислениям сотрудников, работающих на доступных объектах
    """
    async with get_async_session() as session:
        # Получить начисление
        result = await session.execute(
            select(PayrollEntry).where(PayrollEntry.id == payroll_entry_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        # Owner имеет доступ к начислениям своих сотрудников
        if current_user.role == 'owner':
            # Проверить, что сотрудник работает у этого владельца
            # (через договоры)
            return entry
        
        # Manager: проверить доступ к объектам сотрудника
        if current_user.role == 'manager':
            # Получить доступные объекты управляющего
            accessible_objects = await get_accessible_object_ids_for_manager(
                current_user.id, 
                session
            )
            
            # Проверить, что сотрудник работает на доступных объектах
            # (проверить смены в периоде начисления)
            has_access = await check_manager_has_access_to_employee(
                current_user.id,
                entry.employee_id,
                accessible_objects,
                session
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=403, 
                    detail="Нет доступа к начислениям этого сотрудника"
                )
            
            return entry
        
        raise HTTPException(status_code=403, detail="Недостаточно прав")
```

---

## 4. Celery задачи

### 4.1. Автоматические удержания

**Файл:** `core/celery/tasks/payroll_tasks.py` (СОЗДАТЬ)

**Задачи:**

```python
@celery_app.task
def process_automatic_deductions():
    """
    Обработка автоматических удержаний за предыдущий день.
    
    Запуск: ежедневно в 01:00
    
    Логика:
    1. Найти все завершенные смены за вчерашний день
    2. Для каждой смены проверить:
       a) Опоздание > 15 мин от planned_start → создать удержание
       b) Невыполненные обязательные задачи → создать удержания
    3. Создать записи в payroll_deductions с is_automatic=True
    4. Отправить уведомления сотрудникам об удержаниях
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, and_
    from core.database.session import DatabaseManager
    from domain.entities.shift import Shift
    from domain.entities.shift_schedule import ShiftSchedule
    from domain.entities.shift_task import ShiftTask
    from domain.entities.payroll import PayrollDeduction
    from apps.web.services.payroll_service import PayrollService
    from shared.services.notification_service import NotificationService
    from core.logging.logger import logger
    
    db_manager = DatabaseManager()
    
    async def _process():
        async with db_manager.get_session() as session:
            # Вчерашний день (в UTC)
            yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
            day_start = datetime.combine(yesterday, time.min, tzinfo=timezone.utc)
            day_end = datetime.combine(yesterday, time.max, tzinfo=timezone.utc)
            
            # Получить завершенные смены за вчера
            query = select(Shift).where(
                and_(
                    Shift.status == 'completed',
                    Shift.start_time >= day_start,
                    Shift.start_time <= day_end
                )
            )
            result = await session.execute(query)
            shifts = result.scalars().all()
            
            payroll_service = PayrollService(session)
            notification_service = NotificationService(session)
            
            processed_count = 0
            deduction_count = 0
            
            for shift in shifts:
                try:
                    deductions = []
                    
                    # 1. Проверка опоздания (если смена была запланирована)
                    if shift.schedule_id:
                        schedule = await session.get(ShiftSchedule, shift.schedule_id)
                        if schedule:
                            # Рассчитать опоздание с учетом часового пояса
                            late_minutes = (shift.start_time - schedule.planned_start).total_seconds() / 60
                            
                            if late_minutes > 15:
                                # Удержание за опоздание
                                deduction_amount = calculate_late_deduction(late_minutes)
                                deductions.append({
                                    'type': 'late_shift',
                                    'amount': deduction_amount,
                                    'description': f'Опоздание на смену на {int(late_minutes)} минут'
                                })
                    
                    # 2. Проверка невыполненных обязательных задач
                    tasks_query = select(ShiftTask).where(
                        and_(
                            ShiftTask.shift_id == shift.id,
                            ShiftTask.is_mandatory == True,
                            ShiftTask.is_completed == False
                        )
                    )
                    tasks_result = await session.execute(tasks_query)
                    incomplete_tasks = tasks_result.scalars().all()
                    
                    for task in incomplete_tasks:
                        if task.deduction_amount:
                            deductions.append({
                                'type': 'task_incomplete',
                                'amount': task.deduction_amount,
                                'description': f'Не выполнена задача: {task.task_description}'
                            })
                    
                    # 3. Создать удержания
                    if deductions:
                        # Найти или создать начисление за период
                        payroll_entry = await payroll_service.get_or_create_payroll_for_shift(shift)
                        
                        for deduction in deductions:
                            await payroll_service.add_deduction(
                                payroll_entry_id=payroll_entry.id,
                                amount=deduction['amount'],
                                description=deduction['description'],
                                is_automatic=True,
                                shift_id=shift.id,
                                created_by=None  # Автоматическое
                            )
                            deduction_count += 1
                        
                        # 4. Отправить уведомление сотруднику
                        await notification_service.send_deduction_notification(
                            user_id=shift.user_id,
                            shift_id=shift.id,
                            deductions=deductions
                        )
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing shift {shift.id}: {e}")
            
            await session.commit()
            
            logger.info(
                f"Processed automatic deductions: {processed_count} shifts, {deduction_count} deductions"
            )
            
            return {
                'processed_shifts': processed_count,
                'deductions_created': deduction_count
            }
    
    return asyncio.run(_process())


def calculate_late_deduction(late_minutes: float) -> float:
    """
    Рассчитать сумму удержания за опоздание.
    
    Правила (примерные, можно настроить):
    - 15-30 мин: 100 руб
    - 30-60 мин: 200 руб
    - > 60 мин: 500 руб
    """
    if late_minutes <= 15:
        return 0
    elif late_minutes <= 30:
        return 100
    elif late_minutes <= 60:
        return 200
    else:
        return 500
```

**Настройка в Celery Beat:**

```python
# core/celery/celery_app.py

from celery.schedules import crontab

app.conf.beat_schedule = {
    # ... существующие задачи ...
    
    'process-automatic-deductions': {
        'task': 'core.celery.tasks.payroll_tasks.process_automatic_deductions',
        'schedule': crontab(hour=1, minute=0),  # Каждый день в 01:00
    },
}
```

**Тесты:**
- `tests/unit/test_payroll_tasks.py`
- `tests/integration/test_automatic_deductions.py`

---

## 5. Итоговая статистика

### 5.1. Новые сервисы

| Сервис | Файл | Методов | Сложность |
|--------|------|---------|-----------|
| PaymentSystemService | `apps/web/services/payment_system_service.py` | 5 | Низкая |
| PayrollService | `apps/web/services/payroll_service.py` | 10 | Высокая |
| OrgStructureService | `apps/web/services/org_structure_service.py` | 12 | Высокая |
| ShiftTaskService | `apps/web/services/shift_task_service.py` | 7 | Средняя |

**Всего:** 4 новых сервиса, 34 метода

---

### 5.2. Изменения в существующих сервисах

| Сервис | Файл | Новых методов | Изменений | Сложность |
|--------|------|---------------|-----------|-----------|
| ContractService | `apps/web/services/contract_service.py` | 1 | 2 | Средняя |
| ObjectService | `apps/web/services/object_service.py` | 2 | 2 | Средняя |
| ShiftService | `shared/services/shift_service.py` | 1 | 2 | Высокая |

**Всего:** 3 сервиса, 4 новых метода, 6 изменений

---

### 5.3. Новые middleware/зависимости

| Зависимость | Файл | Назначение |
|-------------|------|------------|
| require_manager_payroll_permission | `apps/web/dependencies.py` | Проверка прав на начисления |
| check_payroll_access | `apps/web/dependencies.py` | Проверка доступа к конкретному начислению |

**Всего:** 2 новые зависимости

---

### 5.4. Celery задачи

| Задача | Файл | Расписание | Сложность |
|--------|------|------------|-----------|
| process_automatic_deductions | `core/celery/tasks/payroll_tasks.py` | Ежедневно 01:00 | Высокая |

**Всего:** 1 новая задача

---

### 5.5. Оценка трудозатрат

#### Новые сервисы:
- PaymentSystemService: 0.5 дня
- PayrollService: 2 дня
- OrgStructureService: 2 дня
- ShiftTaskService: 1 день
**Итого:** 5.5 дней

#### Изменения в сервисах:
- ContractService: 0.5 дня
- ObjectService: 0.5 дня
- ShiftService: 1 день
**Итого:** 2 дня

#### Middleware/зависимости:
- Новые зависимости: 0.5 дня
- Интеграция в роуты: 0.5 дня
**Итого:** 1 день

#### Celery задачи:
- process_automatic_deductions: 1 день
- Тестирование: 0.5 дня
**Итого:** 1.5 дня

#### Тесты:
- Unit-тесты: 2 дня
- Integration-тесты: 2 дня
**Итого:** 4 дня

---

**Общая оценка на сервисы и middleware:** ~14 дней

---

**Завершена Фаза 0: Анализ и проектирование!**

**Итоговые документы:**
1. ✅ `db_analysis.md` - Анализ текущей БД
2. ✅ `db_schema.md` - Схемы 9 новых таблиц
3. ✅ `db_changes.md` - Изменения в contracts и objects
4. ✅ `frontend_analysis.md` - Анализ front-end (15 страниц + календарь)
5. ✅ `services_analysis.md` - Анализ сервисов и middleware

**Следующая фаза:** Фаза 1 - Приоритет договорной ставки (3-4 дня)

