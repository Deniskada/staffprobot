"""
Утилиты для работы с заявками
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from domain.entities.application import Application, ApplicationStatus
from domain.entities.object import Object


async def get_new_applications_count(user_id: int, session: AsyncSession, user_role: str = "owner") -> int:
    """
    Получает количество новых заявок (PENDING) для пользователя
    
    Args:
        user_id: ID пользователя
        session: Сессия базы данных
        user_role: Роль пользователя (owner, manager)
    
    Returns:
        Количество новых заявок
    """
    try:
        if user_role == "owner":
            # Для владельца - заявки по всем его объектам
            query = select(func.count(Application.id)).join(Object).where(
                Object.owner_id == user_id
            ).where(Application.status == ApplicationStatus.PENDING)
        elif user_role == "manager":
            # Для управляющего - заявки по объектам, к которым у него есть доступ
            from domain.entities.manager_object_permission import ManagerObjectPermission
            from domain.entities.contract import Contract
            query = select(func.count(Application.id)).join(Object).join(
                ManagerObjectPermission, Object.id == ManagerObjectPermission.object_id
            ).join(Contract, ManagerObjectPermission.contract_id == Contract.id).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.is_manager == True
                )
            ).where(Application.status == ApplicationStatus.PENDING)
        else:
            return 0
        
        result = await session.execute(query)
        return result.scalar() or 0
        
    except Exception as e:
        print(f"Ошибка получения количества новых заявок: {e}")
        return 0
