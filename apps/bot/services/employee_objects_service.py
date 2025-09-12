"""Сервис для получения объектов сотрудника по договорам."""

from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract


class EmployeeObjectsService:
    """Сервис для работы с объектами сотрудников."""
    
    def __init__(self):
        logger.info("EmployeeObjectsService initialized")
    
    async def get_employee_objects(self, telegram_id: int) -> List[Dict[str, Any]]:
        """
        Получает объекты, доступные сотруднику по активным договорам.
        
        Args:
            telegram_id: Telegram ID сотрудника
            
        Returns:
            Список объектов с информацией о договорах
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == telegram_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User with telegram_id {telegram_id} not found")
                    return []
                
                # Получаем активные договоры пользователя
                contracts_query = select(Contract).where(
                    and_(
                        Contract.employee_id == user.id,
                        Contract.status == 'active'
                    )
                ).options(joinedload(Contract.object))
                
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                if not contracts:
                    logger.info(f"No active contracts found for user {telegram_id}")
                    return []
                
                # Собираем уникальные объекты из договоров
                objects_dict = {}
                for contract in contracts:
                    if contract.object and contract.object.is_active:
                        obj = contract.object
                        if obj.id not in objects_dict:
                            objects_dict[obj.id] = {
                                'id': obj.id,
                                'name': obj.name,
                                'address': obj.address,
                                'coordinates': obj.coordinates,
                                'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0.0,
                                'opening_time': obj.opening_time.strftime('%H:%M') if obj.opening_time else None,
                                'closing_time': obj.closing_time.strftime('%H:%M') if obj.closing_time else None,
                                'is_active': obj.is_active,
                                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                                'max_distance_meters': obj.max_distance_meters or 500,
                                'contracts': []
                            }
                        
                        # Добавляем информацию о договоре
                        objects_dict[obj.id]['contracts'].append({
                            'id': contract.id,
                            'title': contract.title,
                            'start_date': contract.start_date.isoformat() if contract.start_date else None,
                            'end_date': contract.end_date.isoformat() if contract.end_date else None,
                            'hourly_rate': float(contract.hourly_rate) if contract.hourly_rate else None,
                            'status': contract.status
                        })
                
                objects_list = list(objects_dict.values())
                
                logger.info(
                    f"Found {len(objects_list)} objects for employee {telegram_id} "
                    f"with {len(contracts)} active contracts"
                )
                
                return objects_list
                
        except Exception as e:
            logger.error(f"Error getting employee objects for {telegram_id}: {e}")
            return []
    
    async def get_employee_object_by_id(self, telegram_id: int, object_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает конкретный объект сотрудника по ID.
        
        Args:
            telegram_id: Telegram ID сотрудника
            object_id: ID объекта
            
        Returns:
            Информация об объекте или None
        """
        try:
            objects = await self.get_employee_objects(telegram_id)
            
            for obj in objects:
                if obj['id'] == object_id:
                    return obj
            
            logger.warning(f"Object {object_id} not found for employee {telegram_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting employee object {object_id} for {telegram_id}: {e}")
            return None
    
    async def has_access_to_object(self, telegram_id: int, object_id: int) -> bool:
        """
        Проверяет, есть ли у сотрудника доступ к объекту.
        
        Args:
            telegram_id: Telegram ID сотрудника
            object_id: ID объекта
            
        Returns:
            True если есть доступ, False иначе
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == telegram_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Проверяем наличие активного договора с этим объектом
                contract_query = select(Contract).where(
                    and_(
                        Contract.employee_id == user.id,
                        Contract.object_id == object_id,
                        Contract.status == 'active'
                    )
                )
                
                contract_result = await session.execute(contract_query)
                contract = contract_result.scalar_one_or_none()
                
                return contract is not None
                
        except Exception as e:
            logger.error(f"Error checking access to object {object_id} for {telegram_id}: {e}")
            return False
    
    async def get_employee_contracts(self, telegram_id: int) -> List[Dict[str, Any]]:
        """
        Получает активные договоры сотрудника.
        
        Args:
            telegram_id: Telegram ID сотрудника
            
        Returns:
            Список договоров
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == telegram_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return []
                
                # Получаем активные договоры
                contracts_query = select(Contract).where(
                    and_(
                        Contract.employee_id == user.id,
                        Contract.status == 'active'
                    )
                ).options(joinedload(Contract.object))
                
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                contracts_list = []
                for contract in contracts:
                    contracts_list.append({
                        'id': contract.id,
                        'title': contract.title,
                        'object_id': contract.object_id,
                        'object_name': contract.object.name if contract.object else 'Неизвестный объект',
                        'start_date': contract.start_date.isoformat() if contract.start_date else None,
                        'end_date': contract.end_date.isoformat() if contract.end_date else None,
                        'hourly_rate': float(contract.hourly_rate) if contract.hourly_rate else None,
                        'status': contract.status,
                        'created_at': contract.created_at.isoformat() if contract.created_at else None
                    })
                
                logger.info(f"Found {len(contracts_list)} active contracts for employee {telegram_id}")
                return contracts_list
                
        except Exception as e:
            logger.error(f"Error getting employee contracts for {telegram_id}: {e}")
            return []
