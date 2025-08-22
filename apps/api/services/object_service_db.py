"""
Сервис для работы с объектами через базу данных
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.object import Object
from domain.entities.user import User
from core.cache.cache_service import CacheService
from core.logging.logger import logger


class ObjectServiceDB:
    """Сервис для работы с объектами в базе данных."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_object(self, object_data: Dict[str, Any]) -> Optional[Object]:
        """Создает новый объект."""
        try:
            # Проверяем существование владельца
            owner_query = select(User).where(User.id == object_data['owner_id'])
            owner_result = await self.db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                logger.error(f"Owner with id {object_data['owner_id']} not found")
                return None
            
            # Создаем объект
            new_object = Object(**object_data)
            self.db.add(new_object)
            await self.db.commit()
            await self.db.refresh(new_object)
            
            logger.info(f"Object created successfully: {new_object.id}")
            return new_object
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while creating object: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error while creating object: {e}")
            await self.db.rollback()
            return None
    
    async def get_object(self, object_id: int) -> Optional[Object]:
        """Получает объект по ID."""
        try:
            query = select(Object).where(Object.id == object_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting object {object_id}: {e}")
            return None
    
    async def get_objects_by_owner(self, owner_id: int) -> List[Object]:
        """Получает все объекты владельца."""
        try:
            query = select(Object).where(Object.owner_id == owner_id)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting objects for owner {owner_id}: {e}")
            return []
    
    async def get_all_objects(self) -> List[Object]:
        """Получает все активные объекты."""
        try:
            query = select(Object).where(Object.is_active == True)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting all objects: {e}")
            return []
    
    async def update_object(self, object_id: int, update_data: Dict[str, Any]) -> bool:
        """Обновляет объект."""
        try:
            query = update(Object).where(Object.id == object_id).values(**update_data)
            result = await self.db.execute(query)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Object {object_id} updated successfully")
                return True
            else:
                logger.warning(f"Object {object_id} not found for update")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Database error while updating object {object_id}: {e}")
            await self.db.rollback()
            return False
    
    async def delete_object(self, object_id: int) -> bool:
        """Удаляет объект (мягкое удаление)."""
        try:
            query = update(Object).where(Object.id == object_id).values(is_active=False)
            result = await self.db.execute(query)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Object {object_id} deleted successfully")
                return True
            else:
                logger.warning(f"Object {object_id} not found for deletion")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Database error while deleting object {object_id}: {e}")
            await self.db.rollback()
            return False
    
    async def search_objects(self, search_term: str) -> List[Object]:
        """Ищет объекты по названию или адресу."""
        try:
            query = select(Object).where(
                Object.is_active == True,
                (Object.name.ilike(f"%{search_term}%") | Object.address.ilike(f"%{search_term}%"))
            )
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while searching objects: {e}")
            return []
