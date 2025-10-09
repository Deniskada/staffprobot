"""Integration-тесты для проверки приоритета ставок при открытии смены."""

import pytest
from datetime import datetime, date, time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.shift import Shift
from domain.entities.time_slot import TimeSlot


@pytest.mark.asyncio
async def test_contract_rate_priority_over_object(db_session: AsyncSession):
    """
    Тест: Ставка договора имеет приоритет над ставкой объекта.
    
    Сценарий:
    1. Создать владельца, сотрудника, объект
    2. Создать договор с use_contract_rate=True и hourly_rate=500
    3. Объект имеет hourly_rate=300
    4. Открыть смену
    5. Проверить, что использована ставка договора (500)
    """
    # Создать владельца
    owner = User(
        telegram_id=9001,
        username="owner_test",
        first_name="Владелец",
        last_name="Тестовый"
    )
    db_session.add(owner)
    await db_session.flush()
    
    # Создать сотрудника
    employee = User(
        telegram_id=9002,
        username="employee_test",
        first_name="Сотрудник",
        last_name="Тестовый"
    )
    db_session.add(employee)
    await db_session.flush()
    
    # Создать объект со ставкой 300
    obj = Object(
        owner_id=owner.id,
        name="Тестовый объект",
        address="Тестовый адрес",
        coordinates="55.7558,37.6173",
        opening_time=time(9, 0),
        closing_time=time(21, 0),
        hourly_rate=300.0,
        is_active=True
    )
    db_session.add(obj)
    await db_session.flush()
    
    # Создать договор с приоритетной ставкой 500
    contract = Contract(
        contract_number="TEST-001",
        owner_id=owner.id,
        employee_id=employee.id,
        title="Тестовый договор",
        hourly_rate=500.0,
        use_contract_rate=True,  # ПРИОРИТЕТ!
        start_date=datetime.now(),
        status="active",
        is_active=True,
        allowed_objects=[obj.id]
    )
    db_session.add(contract)
    await db_session.commit()
    
    # Проверить эффективную ставку
    effective_rate = contract.get_effective_hourly_rate(
        timeslot_rate=None,
        object_rate=300.0
    )
    
    assert effective_rate == 500.0, f"Ожидалась ставка договора 500, получено {effective_rate}"


@pytest.mark.asyncio
async def test_contract_rate_priority_over_timeslot(db_session: AsyncSession):
    """
    Тест: Ставка договора имеет приоритет над ставкой тайм-слота.
    
    Сценарий:
    1. Договор: use_contract_rate=True, hourly_rate=500
    2. Тайм-слот: hourly_rate=350
    3. Объект: hourly_rate=300
    4. Проверить, что используется ставка договора (500)
    """
    # Создать пользователей и объект (аналогично предыдущему тесту)
    owner = User(telegram_id=9003, username="owner2", first_name="Владелец", last_name="2")
    employee = User(telegram_id=9004, username="employee2", first_name="Сотрудник", last_name="2")
    obj = Object(
        owner_id=1,  # Временно
        name="Объект 2",
        address="Адрес 2",
        coordinates="55.7558,37.6173",
        opening_time=time(9, 0),
        closing_time=time(21, 0),
        hourly_rate=300.0,
        is_active=True
    )
    
    db_session.add_all([owner, employee])
    await db_session.flush()
    
    obj.owner_id = owner.id
    db_session.add(obj)
    await db_session.flush()
    
    # Создать договор
    contract = Contract(
        contract_number="TEST-002",
        owner_id=owner.id,
        employee_id=employee.id,
        title="Тестовый договор 2",
        hourly_rate=500.0,
        use_contract_rate=True,
        start_date=datetime.now(),
        status="active",
        is_active=True
    )
    db_session.add(contract)
    await db_session.commit()
    
    # Проверить с тайм-слотом
    effective_rate = contract.get_effective_hourly_rate(
        timeslot_rate=350.0,  # Тайм-слот
        object_rate=300.0      # Объект
    )
    
    assert effective_rate == 500.0, "Ставка договора должна иметь приоритет над тайм-слотом"


@pytest.mark.asyncio
async def test_timeslot_rate_when_contract_flag_disabled(db_session: AsyncSession):
    """
    Тест: Ставка тайм-слота используется когда use_contract_rate=False.
    
    Сценарий:
    1. Договор: use_contract_rate=False, hourly_rate=500
    2. Тайм-слот: hourly_rate=350
    3. Объект: hourly_rate=300
    4. Проверить, что используется ставка тайм-слота (350)
    """
    owner = User(telegram_id=9005, username="owner3", first_name="Владелец", last_name="3")
    employee = User(telegram_id=9006, username="employee3", first_name="Сотрудник", last_name="3")
    
    db_session.add_all([owner, employee])
    await db_session.flush()
    
    contract = Contract(
        contract_number="TEST-003",
        owner_id=owner.id,
        employee_id=employee.id,
        title="Тестовый договор 3",
        hourly_rate=500.0,
        use_contract_rate=False,  # ОТКЛЮЧЕН!
        start_date=datetime.now(),
        status="active",
        is_active=True
    )
    db_session.add(contract)
    await db_session.commit()
    
    effective_rate = contract.get_effective_hourly_rate(
        timeslot_rate=350.0,
        object_rate=300.0
    )
    
    assert effective_rate == 350.0, "Должна использоваться ставка тайм-слота"


@pytest.mark.asyncio
async def test_object_rate_fallback(db_session: AsyncSession):
    """
    Тест: Ставка объекта используется когда нет других опций.
    
    Сценарий:
    1. Договор: use_contract_rate=False, hourly_rate=None
    2. Тайм-слот: hourly_rate=None
    3. Объект: hourly_rate=300
    4. Проверить, что используется ставка объекта (300)
    """
    owner = User(telegram_id=9007, username="owner4", first_name="Владелец", last_name="4")
    employee = User(telegram_id=9008, username="employee4", first_name="Сотрудник", last_name="4")
    
    db_session.add_all([owner, employee])
    await db_session.flush()
    
    contract = Contract(
        contract_number="TEST-004",
        owner_id=owner.id,
        employee_id=employee.id,
        title="Тестовый договор 4",
        hourly_rate=None,
        use_contract_rate=False,
        start_date=datetime.now(),
        status="active",
        is_active=True
    )
    db_session.add(contract)
    await db_session.commit()
    
    effective_rate = contract.get_effective_hourly_rate(
        timeslot_rate=None,
        object_rate=300.0
    )
    
    assert effective_rate == 300.0, "Должна использоваться ставка объекта как fallback"


@pytest.mark.asyncio
async def test_validation_use_contract_rate_requires_hourly_rate():
    """
    Тест: Валидация - use_contract_rate требует hourly_rate.
    
    Проверяется в ContractService.create_contract()
    """
    from apps.web.services.contract_service import ContractService
    
    service = ContractService()
    
    contract_data = {
        "employee_telegram_id": 123456,
        "title": "Тест",
        "start_date": date.today(),
        "use_contract_rate": True,  # Включен флаг
        "hourly_rate": None,  # Но ставки нет!
        "allowed_objects": []
    }
    
    with pytest.raises(ValueError, match="При использовании ставки договора необходимо указать почасовую ставку"):
        await service.create_contract(
            owner_telegram_id=123,
            contract_data=contract_data
        )

