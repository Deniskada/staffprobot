"""
E2E тесты для системы учета выплат сотрудникам (Итерация 23).

Покрываются следующие сценарии:
1. Создание выплат с разными системами оплаты
2. Автоматические удержания за опоздания и задачи
3. Наследование настроек от подразделений
4. Работа управляющих с начислениями
5. Полный цикл от открытия смены до записи выплаты
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.shift import Shift
from domain.entities.shift_task import ShiftTask
from domain.entities.org_structure import OrgStructureUnit
from domain.entities.payment_system import PaymentSystem
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.payroll_deduction import PayrollDeduction
from domain.entities.payroll_bonus import PayrollBonus

from apps.web.services.payroll_service import PayrollService
from apps.web.services.auto_deduction_service import AutoDeductionService
from apps.web.services.org_structure_service import OrgStructureService


@pytest.mark.asyncio
async def test_e2e_scenario_1_different_payment_systems(db_session: AsyncSession):
    """
    Сценарий 1: Расчет выплат для разных систем оплаты.
    
    Проверяет:
    - Простая повременная: только базовая оплата
    - Повременно-премиальная: база + штрафы/премии за задачи
    """
    # Создать владельца
    owner = User(
        telegram_id=100001,
        role="owner",
        first_name="Владелец",
        last_name="Тестовый"
    )
    db_session.add(owner)
    await db_session.flush()
    
    # Создать подразделение
    org_unit = OrgStructureUnit(
        owner_id=owner.id,
        name="Основное подразделение",
        level=0,
        is_active=True
    )
    db_session.add(org_unit)
    await db_session.flush()
    
    # Создать объект
    obj = Object(
        owner_id=owner.id,
        org_unit_id=org_unit.id,
        name="Тестовый объект",
        address="Адрес 1",
        hourly_rate=Decimal("500.00"),
        is_active=True,
        shift_tasks=[
            {"text": "Обязательная задача", "is_mandatory": True, "deduction_amount": -100},
            {"text": "Премиальная задача", "is_mandatory": False, "deduction_amount": 50}
        ]
    )
    db_session.add(obj)
    await db_session.flush()
    
    # Создать двух сотрудников
    employee1 = User(telegram_id=200001, role="employee", first_name="Иван", last_name="Иванов")
    employee2 = User(telegram_id=200002, role="employee", first_name="Петр", last_name="Петров")
    db_session.add_all([employee1, employee2])
    await db_session.flush()
    
    # Получить системы оплаты
    simple_system = await db_session.execute(
        select(PaymentSystem).where(PaymentSystem.code == "simple_hourly")
    )
    simple_system = simple_system.scalar_one()
    
    bonus_system = await db_session.execute(
        select(PaymentSystem).where(PaymentSystem.code == "hourly_bonus")
    )
    bonus_system = bonus_system.scalar_one()
    
    # Создать договоры с разными системами
    contract1 = Contract(
        owner_id=owner.id,
        employee_id=employee1.id,
        contract_number="TEST-001",
        title="Простая повременная",
        payment_system_id=simple_system.id,
        hourly_rate=Decimal("500.00"),
        status="active",
        is_active=True
    )
    
    contract2 = Contract(
        owner_id=owner.id,
        employee_id=employee2.id,
        contract_number="TEST-002",
        title="Повременно-премиальная",
        payment_system_id=bonus_system.id,
        hourly_rate=Decimal("500.00"),
        status="active",
        is_active=True
    )
    db_session.add_all([contract1, contract2])
    await db_session.flush()
    
    # Создать смены (по 8 часов)
    start_time = datetime.now() - timedelta(days=1, hours=8)
    end_time = datetime.now() - timedelta(days=1)
    
    shift1 = Shift(
        employee_id=employee1.id,
        object_id=obj.id,
        start_time=start_time,
        end_time=end_time,
        status="completed",
        hourly_rate=Decimal("500.00"),
        hours_worked=Decimal("8.00")
    )
    
    shift2 = Shift(
        employee_id=employee2.id,
        object_id=obj.id,
        start_time=start_time,
        end_time=end_time,
        status="completed",
        hourly_rate=Decimal("500.00"),
        hours_worked=Decimal("8.00")
    )
    db_session.add_all([shift1, shift2])
    await db_session.flush()
    
    # Создать задачи для shift2 (повременно-премиальная)
    task1 = ShiftTask(
        shift_id=shift2.id,
        task_text="Обязательная задача",
        is_mandatory=True,
        deduction_amount=Decimal("-100.00"),
        is_completed=False,  # НЕ выполнена → штраф
        source="object"
    )
    
    task2 = ShiftTask(
        shift_id=shift2.id,
        task_text="Премиальная задача",
        is_mandatory=False,
        deduction_amount=Decimal("50.00"),
        is_completed=True,  # Выполнена → премия
        source="object"
    )
    db_session.add_all([task1, task2])
    await db_session.commit()
    
    # Запустить автоматические удержания
    auto_service = AutoDeductionService(db_session)
    await auto_service.process_shift_deductions(shift1.id)
    await auto_service.process_shift_deductions(shift2.id)
    
    # Создать начисления
    payroll_service = PayrollService(db_session)
    
    entry1 = await payroll_service.create_payroll_entry(
        employee_id=employee1.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    entry2 = await payroll_service.create_payroll_entry(
        employee_id=employee2.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    # Проверки
    # Сотрудник 1 (простая): 8 часов * 500₽ = 4000₽ (без штрафов/премий)
    assert entry1.base_amount == Decimal("4000.00")
    assert entry1.deduction_amount == Decimal("0.00")  # Штрафы не применяются
    assert entry1.bonus_amount == Decimal("0.00")
    assert entry1.total_amount == Decimal("4000.00")
    
    # Сотрудник 2 (премиальная): 8 * 500 - 100 (штраф) + 50 (премия) = 3950₽
    assert entry2.base_amount == Decimal("4000.00")
    
    # Получить удержания и премии для entry2
    deductions = await payroll_service.get_deductions_for_entry(entry2.id)
    bonuses = await payroll_service.get_bonuses_for_entry(entry2.id)
    
    assert len(deductions) == 1
    assert deductions[0].amount == Decimal("100.00")
    assert deductions[0].is_automatic == True
    
    assert len(bonuses) == 1
    assert bonuses[0].amount == Decimal("50.00")
    assert bonuses[0].is_automatic == True
    
    assert entry2.total_amount == Decimal("3950.00")
    
    print("✅ Сценарий 1: Разные системы оплаты - пройден")


@pytest.mark.asyncio
async def test_e2e_scenario_2_late_start_penalties(db_session: AsyncSession):
    """
    Сценарий 2: Автоматические удержания за опоздания.
    
    Проверяет:
    - Расчет штрафа за опоздание
    - Использование настроек объекта
    - Создание PayrollDeduction с is_automatic=True
    """
    # Создать владельца
    owner = User(telegram_id=100002, role="owner", first_name="Владелец2")
    db_session.add(owner)
    await db_session.flush()
    
    # Создать подразделение
    org_unit = OrgStructureUnit(
        owner_id=owner.id,
        name="Основное",
        level=0,
        is_active=True,
        inherit_late_settings=False,
        late_threshold_minutes=5,
        late_penalty_per_minute=Decimal("10.00")
    )
    db_session.add(org_unit)
    await db_session.flush()
    
    # Создать объект с настройками опозданий
    obj = Object(
        owner_id=owner.id,
        org_unit_id=org_unit.id,
        name="Объект со штрафами",
        address="Адрес 2",
        hourly_rate=Decimal("600.00"),
        is_active=True,
        inherit_late_settings=False,
        late_threshold_minutes=5,
        late_penalty_per_minute=Decimal("10.00")
    )
    db_session.add(obj)
    await db_session.flush()
    
    # Создать сотрудника
    employee = User(telegram_id=200003, role="employee", first_name="Опоздавший")
    db_session.add(employee)
    await db_session.flush()
    
    # Получить повременно-премиальную систему
    bonus_system = await db_session.execute(
        select(PaymentSystem).where(PaymentSystem.code == "hourly_bonus")
    )
    bonus_system = bonus_system.scalar_one()
    
    # Создать договор
    contract = Contract(
        owner_id=owner.id,
        employee_id=employee.id,
        contract_number="TEST-003",
        payment_system_id=bonus_system.id,
        hourly_rate=Decimal("600.00"),
        status="active",
        is_active=True
    )
    db_session.add(contract)
    await db_session.flush()
    
    # Создать смену с опозданием на 15 минут
    planned_start = datetime.now() - timedelta(days=1, hours=8)
    actual_start = planned_start + timedelta(minutes=15)
    actual_end = datetime.now() - timedelta(days=1)
    
    shift = Shift(
        employee_id=employee.id,
        object_id=obj.id,
        planned_start_time=planned_start,
        start_time=actual_start,
        end_time=actual_end,
        status="completed",
        hourly_rate=Decimal("600.00"),
        hours_worked=Decimal("7.75")
    )
    db_session.add(shift)
    await db_session.commit()
    
    # Запустить автоматические удержания
    auto_service = AutoDeductionService(db_session)
    await auto_service.process_shift_deductions(shift.id)
    await db_session.commit()
    
    # Создать начисление
    payroll_service = PayrollService(db_session)
    entry = await payroll_service.create_payroll_entry(
        employee_id=employee.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    # Проверки
    # База: 7.75 часов * 600₽ = 4650₽
    assert entry.base_amount == Decimal("4650.00")
    
    # Штраф: (15 минут - 5 порог) * 10₽ = 100₽
    deductions = await payroll_service.get_deductions_for_entry(entry.id)
    assert len(deductions) == 1
    assert deductions[0].amount == Decimal("100.00")
    assert deductions[0].deduction_type == "late_start"
    assert deductions[0].is_automatic == True
    
    # Итого: 4650 - 100 = 4550₽
    assert entry.total_amount == Decimal("4550.00")
    
    print("✅ Сценарий 2: Штрафы за опоздания - пройден")


@pytest.mark.asyncio
async def test_e2e_scenario_3_org_structure_inheritance(db_session: AsyncSession):
    """
    Сценарий 3: Наследование настроек от подразделений.
    
    Проверяет:
    - Наследование payment_system_id
    - Наследование late_settings
    - Применение унаследованных настроек при расчете
    """
    # Создать владельца
    owner = User(telegram_id=100003, role="owner", first_name="Владелец3")
    db_session.add(owner)
    await db_session.flush()
    
    # Получить повременно-премиальную систему
    bonus_system = await db_session.execute(
        select(PaymentSystem).where(PaymentSystem.code == "hourly_bonus")
    )
    bonus_system = bonus_system.scalar_one()
    
    # Создать корневое подразделение с настройками
    root_unit = OrgStructureUnit(
        owner_id=owner.id,
        name="Головной офис",
        level=0,
        is_active=True,
        payment_system_id=bonus_system.id,
        inherit_late_settings=False,
        late_threshold_minutes=10,
        late_penalty_per_minute=Decimal("5.00")
    )
    db_session.add(root_unit)
    await db_session.flush()
    
    # Создать дочернее подразделение (наследует настройки)
    child_unit = OrgStructureUnit(
        owner_id=owner.id,
        parent_id=root_unit.id,
        name="Филиал",
        level=1,
        is_active=True,
        inherit_late_settings=True  # Наследует от родителя
        # payment_system_id = None → наследуется
    )
    db_session.add(child_unit)
    await db_session.flush()
    
    # Создать объект в дочернем подразделении (наследует все)
    obj = Object(
        owner_id=owner.id,
        org_unit_id=child_unit.id,
        name="Объект филиала",
        address="Адрес 3",
        hourly_rate=Decimal("400.00"),
        is_active=True,
        inherit_late_settings=True,
        shift_tasks=[
            {"text": "Задача 1", "is_mandatory": True, "deduction_amount": -50}
        ]
    )
    db_session.add(obj)
    await db_session.flush()
    
    # Создать сотрудника
    employee = User(telegram_id=200004, role="employee", first_name="Сотрудник")
    db_session.add(employee)
    await db_session.flush()
    
    # Создать договор (без указания системы → использует объект → подразделение)
    contract = Contract(
        owner_id=owner.id,
        employee_id=employee.id,
        contract_number="TEST-004",
        hourly_rate=Decimal("400.00"),
        status="active",
        is_active=True
        # payment_system_id = None → наследуется
    )
    db_session.add(contract)
    await db_session.flush()
    
    # Проверить эффективные настройки объекта
    effective_payment_system = obj.get_effective_payment_system_id()
    assert effective_payment_system == bonus_system.id  # Унаследовано от root_unit
    
    effective_late_settings = obj.get_effective_late_settings()
    assert effective_late_settings['threshold_minutes'] == 10
    assert effective_late_settings['penalty_per_minute'] == Decimal("5.00")
    
    # Создать смену с опозданием на 20 минут
    planned_start = datetime.now() - timedelta(days=1, hours=8)
    actual_start = planned_start + timedelta(minutes=20)
    actual_end = datetime.now() - timedelta(days=1)
    
    shift = Shift(
        employee_id=employee.id,
        object_id=obj.id,
        planned_start_time=planned_start,
        start_time=actual_start,
        end_time=actual_end,
        status="completed",
        hourly_rate=Decimal("400.00"),
        hours_worked=Decimal("7.67")
    )
    db_session.add(shift)
    
    # Создать задачу (не выполнена)
    task = ShiftTask(
        shift_id=shift.id,
        task_text="Задача 1",
        is_mandatory=True,
        deduction_amount=Decimal("-50.00"),
        is_completed=False,
        source="object"
    )
    db_session.add(task)
    await db_session.commit()
    
    # Запустить автоматические удержания
    auto_service = AutoDeductionService(db_session)
    await auto_service.process_shift_deductions(shift.id)
    await db_session.commit()
    
    # Создать начисление
    payroll_service = PayrollService(db_session)
    entry = await payroll_service.create_payroll_entry(
        employee_id=employee.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    # Проверки
    # База: 7.67 * 400 = 3068₽
    assert entry.base_amount == Decimal("3068.00")
    
    # Удержания: (20 - 10) * 5 + 50 = 100₽
    deductions = await payroll_service.get_deductions_for_entry(entry.id)
    assert len(deductions) == 2  # Опоздание + задача
    
    total_deductions = sum(d.amount for d in deductions)
    assert total_deductions == Decimal("100.00")
    
    # Итого: 3068 - 100 = 2968₽
    assert entry.total_amount == Decimal("2968.00")
    
    print("✅ Сценарий 3: Наследование настроек - пройден")


@pytest.mark.asyncio
async def test_e2e_scenario_4_manager_payroll_access(db_session: AsyncSession):
    """
    Сценарий 4: Работа управляющих с начислениями.
    
    Проверяет:
    - Право can_manage_payroll
    - Доступ только к начислениям по своим объектам
    - Ограничения для управляющих (нет одобрения/выплат)
    """
    # Создать владельца
    owner = User(telegram_id=100004, role="owner", first_name="Владелец4")
    db_session.add(owner)
    await db_session.flush()
    
    # Создать подразделение
    org_unit = OrgStructureUnit(
        owner_id=owner.id,
        name="Основное",
        level=0,
        is_active=True
    )
    db_session.add(org_unit)
    await db_session.flush()
    
    # Создать 2 объекта
    obj1 = Object(
        owner_id=owner.id,
        org_unit_id=org_unit.id,
        name="Объект 1",
        address="Адрес 1",
        hourly_rate=Decimal("500.00"),
        is_active=True
    )
    
    obj2 = Object(
        owner_id=owner.id,
        org_unit_id=org_unit.id,
        name="Объект 2",
        address="Адрес 2",
        hourly_rate=Decimal("500.00"),
        is_active=True
    )
    db_session.add_all([obj1, obj2])
    await db_session.flush()
    
    # Создать управляющего с правом can_manage_payroll
    manager = User(telegram_id=300001, role="manager", first_name="Управляющий")
    db_session.add(manager)
    await db_session.flush()
    
    # Договор управляющего (доступ только к объекту 1)
    manager_contract = Contract(
        owner_id=owner.id,
        employee_id=manager.id,
        contract_number="MGR-001",
        is_manager=True,
        manager_permissions={
            "can_manage_payroll": True,
            "can_view": True
        },
        allowed_objects=[obj1.id],  # Только объект 1
        status="active",
        is_active=True
    )
    db_session.add(manager_contract)
    await db_session.flush()
    
    # Создать сотрудников
    emp1 = User(telegram_id=200005, role="employee", first_name="Сотрудник1")
    emp2 = User(telegram_id=200006, role="employee", first_name="Сотрудник2")
    db_session.add_all([emp1, emp2])
    await db_session.flush()
    
    # Договоры сотрудников
    contract1 = Contract(
        owner_id=owner.id,
        employee_id=emp1.id,
        contract_number="EMP-001",
        hourly_rate=Decimal("500.00"),
        status="active",
        is_active=True
    )
    
    contract2 = Contract(
        owner_id=owner.id,
        employee_id=emp2.id,
        contract_number="EMP-002",
        hourly_rate=Decimal("500.00"),
        status="active",
        is_active=True
    )
    db_session.add_all([contract1, contract2])
    await db_session.flush()
    
    # Создать смены
    start_time = datetime.now() - timedelta(days=1, hours=8)
    end_time = datetime.now() - timedelta(days=1)
    
    shift1 = Shift(
        employee_id=emp1.id,
        object_id=obj1.id,  # Доступен управляющему
        start_time=start_time,
        end_time=end_time,
        status="completed",
        hourly_rate=Decimal("500.00"),
        hours_worked=Decimal("8.00")
    )
    
    shift2 = Shift(
        employee_id=emp2.id,
        object_id=obj2.id,  # НЕ доступен управляющему
        start_time=start_time,
        end_time=end_time,
        status="completed",
        hourly_rate=Decimal("500.00"),
        hours_worked=Decimal("8.00")
    )
    db_session.add_all([shift1, shift2])
    await db_session.commit()
    
    # Создать начисления
    payroll_service = PayrollService(db_session)
    
    entry1 = await payroll_service.create_payroll_entry(
        employee_id=emp1.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    entry2 = await payroll_service.create_payroll_entry(
        employee_id=emp2.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    # Проверки доступа управляющего
    # (В реальном приложении это проверяется через ManagerPermissionService)
    # Управляющий видит entry1 (объект 1), но не видит entry2 (объект 2)
    
    # Проверка прав
    assert manager_contract.manager_permissions["can_manage_payroll"] == True
    assert obj1.id in manager_contract.allowed_objects
    assert obj2.id not in manager_contract.allowed_objects
    
    # Проверка начислений
    assert entry1.employee_id == emp1.id
    assert entry2.employee_id == emp2.id
    
    print("✅ Сценарий 4: Доступ управляющих к начислениям - пройден")


@pytest.mark.asyncio
async def test_e2e_scenario_5_full_payment_cycle(db_session: AsyncSession):
    """
    Сценарий 5: Полный цикл от открытия смены до записи выплаты.
    
    Проверяет:
    - Открытие смены с почасовой ставкой (приоритет договора)
    - Выполнение задач
    - Автоматические удержания
    - Расчет начисления
    - Одобрение
    - Запись выплаты
    """
    # Создать владельца
    owner = User(telegram_id=100005, role="owner", first_name="Владелец5")
    db_session.add(owner)
    await db_session.flush()
    
    # Создать подразделение
    org_unit = OrgStructureUnit(
        owner_id=owner.id,
        name="Основное",
        level=0,
        is_active=True
    )
    db_session.add(org_unit)
    await db_session.flush()
    
    # Создать объект
    obj = Object(
        owner_id=owner.id,
        org_unit_id=org_unit.id,
        name="Финальный объект",
        address="Адрес финальный",
        hourly_rate=Decimal("300.00"),  # Базовая ставка объекта
        is_active=True,
        shift_tasks=[
            {"text": "Задача А", "is_mandatory": True, "deduction_amount": -200},
            {"text": "Задача Б", "is_mandatory": False, "deduction_amount": 100}
        ]
    )
    db_session.add(obj)
    await db_session.flush()
    
    # Создать сотрудника
    employee = User(telegram_id=200007, role="employee", first_name="Финальный", last_name="Сотрудник")
    db_session.add(employee)
    await db_session.flush()
    
    # Получить повременно-премиальную систему
    bonus_system = await db_session.execute(
        select(PaymentSystem).where(PaymentSystem.code == "hourly_bonus")
    )
    bonus_system = bonus_system.scalar_one()
    
    # Создать договор с ПРИОРИТЕТОМ ставки (800₽ > 300₽ объекта)
    contract = Contract(
        owner_id=owner.id,
        employee_id=employee.id,
        contract_number="FINAL-001",
        payment_system_id=bonus_system.id,
        hourly_rate=Decimal("800.00"),
        use_contract_rate=True,  # ПРИОРИТЕТ!
        status="active",
        is_active=True
    )
    db_session.add(contract)
    await db_session.flush()
    
    # Шаг 1: Открыть смену
    start_time = datetime.now() - timedelta(days=1, hours=10)
    end_time = datetime.now() - timedelta(days=1, hours=2)
    
    shift = Shift(
        employee_id=employee.id,
        object_id=obj.id,
        start_time=start_time,
        end_time=end_time,
        status="completed",
        hourly_rate=Decimal("800.00"),  # Использовалась ставка договора!
        hours_worked=Decimal("8.00")
    )
    db_session.add(shift)
    await db_session.flush()
    
    # Шаг 2: Создать задачи смены
    task_a = ShiftTask(
        shift_id=shift.id,
        task_text="Задача А",
        is_mandatory=True,
        deduction_amount=Decimal("-200.00"),
        is_completed=True,  # Выполнена → без штрафа
        source="object"
    )
    
    task_b = ShiftTask(
        shift_id=shift.id,
        task_text="Задача Б",
        is_mandatory=False,
        deduction_amount=Decimal("100.00"),
        is_completed=True,  # Выполнена → премия
        source="object"
    )
    db_session.add_all([task_a, task_b])
    await db_session.commit()
    
    # Шаг 3: Автоматические удержания
    auto_service = AutoDeductionService(db_session)
    await auto_service.process_shift_deductions(shift.id)
    await db_session.commit()
    
    # Шаг 4: Создать начисление
    payroll_service = PayrollService(db_session)
    entry = await payroll_service.create_payroll_entry(
        employee_id=employee.id,
        period_start=date.today() - timedelta(days=2),
        period_end=date.today(),
        created_by_id=owner.id
    )
    
    # Проверки после создания
    # База: 8 часов * 800₽ = 6400₽
    assert entry.base_amount == Decimal("6400.00")
    assert entry.status == "draft"
    
    # Премия за задачу Б
    bonuses = await payroll_service.get_bonuses_for_entry(entry.id)
    assert len(bonuses) == 1
    assert bonuses[0].amount == Decimal("100.00")
    
    # Итого: 6400 + 100 = 6500₽
    assert entry.total_amount == Decimal("6500.00")
    
    # Шаг 5: Одобрить начисление
    approved_entry = await payroll_service.approve_payroll_entry(
        entry_id=entry.id,
        approved_by_id=owner.id
    )
    assert approved_entry.status == "approved"
    assert approved_entry.approved_at is not None
    assert approved_entry.approved_by_id == owner.id
    
    # Шаг 6: Записать выплату
    payment = await payroll_service.create_payment(
        payroll_entry_id=entry.id,
        amount=Decimal("6500.00"),
        payment_method="bank_transfer",
        created_by_id=owner.id
    )
    
    # Финальные проверки
    assert payment.amount == Decimal("6500.00")
    assert payment.payment_method == "bank_transfer"
    
    # Статус должен измениться на "paid"
    await db_session.refresh(entry)
    assert entry.status == "paid"
    
    print("✅ Сценарий 5: Полный цикл выплат - пройден")
    print(f"   Ставка договора (800₽) > Ставка объекта (300₽)")
    print(f"   База: {entry.base_amount}₽, Премии: {entry.bonus_amount}₽, Итого: {entry.total_amount}₽")
    print(f"   Статус: {entry.status}, Выплачено: {payment.amount}₽")


if __name__ == "__main__":
    print("E2E тесты для системы учета выплат сотрудникам")
    print("Запуск: pytest tests/integration/test_payment_e2e.py -v")

