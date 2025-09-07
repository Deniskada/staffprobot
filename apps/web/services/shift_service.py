"""Веб-сервис для работы со сменами."""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from core.logging.logger import logger
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.object import Object
from domain.entities.user import User


class ShiftService:
    """Веб-сервис для работы со сменами."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_scheduled_shifts_by_month(
        self, 
        year: int, 
        month: int, 
        owner_telegram_id: int,
        object_id: Optional[int] = None
    ) -> List[ShiftSchedule]:
        """Получение запланированных смен за месяц для владельца."""
        try:
            # Получаем внутренний ID владельца
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await self.db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return []
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == owner.id)
            if object_id:
                objects_query = objects_query.where(Object.id == object_id)
            
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            object_ids = [obj.id for obj in objects]
            
            if not object_ids:
                return []
            
            # Получаем запланированные смены
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            shifts_query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.user)
            ).where(
                and_(
                    ShiftSchedule.object_id.in_(object_ids),
                    ShiftSchedule.planned_start >= start_date,
                    ShiftSchedule.planned_start < end_date
                )
            ).order_by(ShiftSchedule.planned_start)
            
            shifts_result = await self.db.execute(shifts_query)
            return shifts_result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting scheduled shifts by month: {e}")
            return []
    
    async def get_shifts_by_month(
        self, 
        year: int, 
        month: int, 
        owner_telegram_id: int,
        object_id: Optional[int] = None
    ) -> List[Shift]:
        """Получение фактических смен за месяц для владельца."""
        try:
            # Получаем внутренний ID владельца
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await self.db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return []
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == owner.id)
            if object_id:
                objects_query = objects_query.where(Object.id == object_id)
            
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            object_ids = [obj.id for obj in objects]
            
            if not object_ids:
                return []
            
            # Получаем фактические смены
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            shifts_query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(
                and_(
                    Shift.object_id.in_(object_ids),
                    Shift.start_time >= start_date,
                    Shift.start_time < end_date
                )
            ).order_by(Shift.start_time)
            
            shifts_result = await self.db.execute(shifts_query)
            return shifts_result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting shifts by month: {e}")
            return []
    
    async def get_shift_by_id(self, shift_id: int, owner_telegram_id: int) -> Optional[Shift]:
        """Получение смены по ID для владельца."""
        try:
            # Получаем внутренний ID владельца
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await self.db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return None
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == owner.id)
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            object_ids = [obj.id for obj in objects]
            
            if not object_ids:
                return None
            
            # Получаем смену
            shift_query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(
                and_(
                    Shift.id == shift_id,
                    Shift.object_id.in_(object_ids)
                )
            )
            
            shift_result = await self.db.execute(shift_query)
            return shift_result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting shift by id: {e}")
            return None
    
    async def get_scheduled_shift_by_id(self, shift_id: int, owner_telegram_id: int) -> Optional[ShiftSchedule]:
        """Получение запланированной смены по ID для владельца."""
        try:
            # Получаем внутренний ID владельца
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await self.db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return None
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == owner.id)
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            object_ids = [obj.id for obj in objects]
            
            if not object_ids:
                return None
            
            # Получаем запланированную смену
            shift_query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.user)
            ).where(
                and_(
                    ShiftSchedule.id == shift_id,
                    ShiftSchedule.object_id.in_(object_ids)
                )
            )
            
            shift_result = await self.db.execute(shift_query)
            return shift_result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting scheduled shift by id: {e}")
            return None
