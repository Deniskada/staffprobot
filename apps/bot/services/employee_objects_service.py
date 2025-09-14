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
                )
                
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                if not contracts:
                    logger.info(f"No active contracts found for user {telegram_id}")
                    return []
                
                # Собираем ID объектов из всех договоров
                object_ids = set()
                for contract in contracts:
                    if contract.allowed_objects:
                        object_ids.update(contract.allowed_objects)
                        logger.info(f"Contract {contract.id} allows objects: {contract.allowed_objects}")
                
                logger.info(f"Total allowed object IDs for user {telegram_id}: {object_ids}")
                if not object_ids:
                    logger.info(f"No allowed objects found in contracts for user {telegram_id}")
                    return []
                
                # Получаем объекты по ID
                objects_query = select(Object).where(
                    and_(
                        Object.id.in_(object_ids),
                        Object.is_active == True
                    )
                )
                
                objects_result = await session.execute(objects_query)
                objects = objects_result.scalars().all()
                
                # Собираем уникальные объекты с информацией о договорах
                objects_dict = {}
                for obj in objects:
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
                
                # Добавляем информацию о договорах для каждого объекта
                for contract in contracts:
                    if contract.allowed_objects:
                        for obj_id in contract.allowed_objects:
                            if obj_id in objects_dict:
                                objects_dict[obj_id]['contracts'].append({
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
            logger.info(f"Getting object {object_id} for employee {telegram_id}")
            objects = await self.get_employee_objects(telegram_id)
            logger.info(f"Found {len(objects)} objects for employee {telegram_id}")
            
            for obj in objects:
                if obj['id'] == object_id:
                    logger.info(f"Found object {object_id}: {obj['name']}")
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
                
                # Проверяем наличие активного договора с доступом к этому объекту
                contracts_query = select(Contract).where(
                    and_(
                        Contract.employee_id == user.id,
                        Contract.status == 'active'
                    )
                )
                
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                # Проверяем, есть ли объект в allowed_objects любого договора
                for contract in contracts:
                    if contract.allowed_objects and object_id in contract.allowed_objects:
                        return True
                
                return False
                
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
                )
                
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                contracts_list = []
                for contract in contracts:
                    # Получаем названия объектов из allowed_objects
                    object_names = []
                    if contract.allowed_objects:
                        for obj_id in contract.allowed_objects:
                            obj_query = select(Object).where(Object.id == obj_id)
                            obj_result = await session.execute(obj_query)
                            obj = obj_result.scalar_one_or_none()
                            if obj:
                                object_names.append(obj.name)
                    
                    contracts_list.append({
                        'id': contract.id,
                        'title': contract.title,
                        'allowed_objects': contract.allowed_objects or [],
                        'object_names': object_names,
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
