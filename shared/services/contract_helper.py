"""Утилиты для работы с контрактами."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.org_structure import OrgStructureUnit


async def get_inherited_payment_schedule_id(
    contract: Contract,
    session: AsyncSession
) -> Optional[int]:
    """
    Получить ID графика выплат с учетом наследования от объекта.
    
    Правильная цепочка наследования:
    Сотрудник (contract) → Объект → Подразделение → иерархия подразделений
    
    Логика:
    1. Если inherit_payment_schedule=False → использовать contract.payment_schedule_id (ПРИОРИТЕТ 1)
    2. Если inherit_payment_schedule=True → искать по цепочке:
       - Объект (payment_schedule_id) (ПРИОРИТЕТ 2)
       - Подразделение объекта (payment_schedule_id) (ПРИОРИТЕТ 3)
       - Родительские подразделения (вверх по иерархии) (ПРИОРИТЕТ 4+)
    
    Args:
        contract: Договор сотрудника
        session: Сессия БД
        
    Returns:
        ID графика выплат или None
    """
    # ПРИОРИТЕТ 1: Явно указанный график в договоре
    if not contract.inherit_payment_schedule:
        return contract.payment_schedule_id
    
    # ПРИОРИТЕТ 2-4+: Наследование от объекта
    # Получить первый объект из allowed_objects
    if not contract.allowed_objects or len(contract.allowed_objects) == 0:
        return None
    
    first_object_id = contract.allowed_objects[0]
    
    # Загрузить объект
    result = await session.execute(
        select(Object).where(Object.id == first_object_id)
    )
    obj = result.scalar_one_or_none()
    
    if not obj:
        return None
    
    # ПРИОРИТЕТ 2: Если у объекта есть прямая привязка к графику - вернуть её
    if obj.payment_schedule_id:
        return obj.payment_schedule_id
    
    # ПРИОРИТЕТ 3+: Если нет графика у объекта - идем к подразделению
    if not obj.org_unit_id:
        return None
    
    # ПРИОРИТЕТ 3-4+: Получить график от подразделения (с учетом наследования по цепочке)
    # Реализуем логику вручную, чтобы избежать lazy loading
    current_unit_id = obj.org_unit_id
    
    while current_unit_id:
        result = await session.execute(
            select(OrgStructureUnit).where(OrgStructureUnit.id == current_unit_id)
        )
        unit = result.scalar_one_or_none()
        
        if not unit:
            break
        
        # Если у подразделения есть явный график - вернуть его
        if unit.payment_schedule_id:
            return unit.payment_schedule_id
        
        # Иначе идем к родителю
        current_unit_id = unit.parent_id
    
    return None

