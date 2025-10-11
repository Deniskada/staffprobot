"""Сервис управления состоянием объектов (открыт/закрыт)."""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.object_opening import ObjectOpening
from domain.entities.shift import Shift
from shared.services.base_service import BaseService
from core.logging.logger import logger


class ObjectOpeningService(BaseService):
    """Сервис для управления состоянием объектов."""
    
    async def is_object_open(self, object_id: int) -> bool:
        """Проверить: открыт ли объект.
        
        Args:
            object_id: ID объекта
            
        Returns:
            True если объект открыт (есть запись с closed_at IS NULL)
        """
        query = select(ObjectOpening).where(
            ObjectOpening.object_id == object_id,
            ObjectOpening.closed_at.is_(None)
        )
        result = await self.db.execute(query)
        opening = result.scalar_one_or_none()
        
        is_open = opening is not None
        logger.info(
            f"Object open status checked",
            object_id=object_id,
            is_open=is_open,
            opening_id=opening.id if opening else None
        )
        return is_open
    
    async def get_active_opening(self, object_id: int) -> Optional[ObjectOpening]:
        """Получить активную запись открытия объекта.
        
        Args:
            object_id: ID объекта
            
        Returns:
            ObjectOpening если объект открыт, иначе None
        """
        query = select(ObjectOpening).where(
            ObjectOpening.object_id == object_id,
            ObjectOpening.closed_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def open_object(
        self,
        object_id: int,
        user_id: int,
        coordinates: Optional[str] = None
    ) -> ObjectOpening:
        """Открыть объект.
        
        Args:
            object_id: ID объекта
            user_id: ID пользователя, открывающего объект
            coordinates: Координаты в формате "lat,lon"
            
        Returns:
            Созданная запись ObjectOpening
            
        Raises:
            ValueError: Если объект уже открыт
        """
        # Проверить: уже открыт?
        if await self.is_object_open(object_id):
            raise ValueError(f"Object {object_id} is already open")
        
        # Создать запись
        opening = ObjectOpening(
            object_id=object_id,
            opened_by=user_id,
            opened_at=datetime.now(),
            open_coordinates=coordinates
        )
        
        self.db.add(opening)
        await self.db.commit()
        await self.db.refresh(opening)
        
        logger.info(
            f"Object opened",
            object_id=object_id,
            user_id=user_id,
            opening_id=opening.id,
            coordinates=coordinates
        )
        
        return opening
    
    async def close_object(
        self,
        object_id: int,
        user_id: int,
        coordinates: Optional[str] = None
    ) -> ObjectOpening:
        """Закрыть объект.
        
        Args:
            object_id: ID объекта
            user_id: ID пользователя, закрывающего объект
            coordinates: Координаты в формате "lat,lon"
            
        Returns:
            Обновленная запись ObjectOpening
            
        Raises:
            ValueError: Если объект не открыт
        """
        # Получить активное открытие
        opening = await self.get_active_opening(object_id)
        if not opening:
            raise ValueError(f"Object {object_id} is not open")
        
        # Закрыть
        opening.closed_by = user_id
        opening.closed_at = datetime.now()
        opening.close_coordinates = coordinates
        
        await self.db.commit()
        await self.db.refresh(opening)
        
        logger.info(
            f"Object closed",
            object_id=object_id,
            user_id=user_id,
            opening_id=opening.id,
            duration_hours=opening.duration_hours,
            coordinates=coordinates
        )
        
        return opening
    
    async def get_active_shifts_count(self, object_id: int) -> int:
        """Подсчитать количество активных смен на объекте.
        
        Args:
            object_id: ID объекта
            
        Returns:
            Количество активных смен
        """
        query = select(func.count(Shift.id)).where(
            Shift.object_id == object_id,
            Shift.status == 'active'
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        logger.debug(
            f"Active shifts counted",
            object_id=object_id,
            count=count
        )
        
        return count

