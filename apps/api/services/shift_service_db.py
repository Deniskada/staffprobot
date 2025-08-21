"""
Сервис для работы со сменами через базу данных
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.shift import Shift
from domain.entities.user import User
from domain.entities.object import Object

logger = logging.getLogger(__name__)


class ShiftServiceDB:
    """Сервис для работы со сменами в базе данных."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_shift(self, shift_data: Dict[str, Any]) -> Optional[Shift]:
        """Создает новую смену."""
        try:
            # Проверяем существование пользователя
            user_query = select(User).where(User.id == shift_data['user_id'])
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User with id {shift_data['user_id']} not found")
                return None
            
            # Проверяем существование объекта
            object_query = select(Object).where(Object.id == shift_data['object_id'])
            object_result = await self.db.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            if not obj:
                logger.error(f"Object with id {shift_data['object_id']} not found")
                return None
            
            # Проверяем, нет ли уже активной смены у пользователя
            active_shift = await self.get_active_shift_by_user(shift_data['user_id'])
            if active_shift:
                logger.error(f"User {shift_data['user_id']} already has an active shift")
                return None
            
            # Создаем смену
            new_shift = Shift(**shift_data)
            self.db.add(new_shift)
            await self.db.commit()
            await self.db.refresh(new_shift)
            
            logger.info(f"Shift created successfully: {new_shift.id}")
            return new_shift
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while creating shift: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error while creating shift: {e}")
            await self.db.rollback()
            return None
    
    async def get_shift(self, shift_id: int) -> Optional[Shift]:
        """Получает смену по ID."""
        try:
            query = select(Shift).where(Shift.id == shift_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting shift {shift_id}: {e}")
            return None
    
    async def get_active_shift_by_user(self, user_id: int) -> Optional[Shift]:
        """Получает активную смену пользователя."""
        try:
            query = select(Shift).where(
                and_(
                    Shift.user_id == user_id,
                    Shift.status == 'active',
                    Shift.end_time.is_(None)
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting active shift for user {user_id}: {e}")
            return None
    
    async def get_shifts_by_user(self, user_id: int, limit: int = 50) -> List[Shift]:
        """Получает смены пользователя."""
        try:
            query = select(Shift).where(Shift.user_id == user_id).order_by(Shift.start_time.desc()).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting shifts for user {user_id}: {e}")
            return []
    
    async def get_shifts_by_object(self, object_id: int, limit: int = 50) -> List[Shift]:
        """Получает смены по объекту."""
        try:
            query = select(Shift).where(Shift.object_id == object_id).order_by(Shift.start_time.desc()).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting shifts for object {object_id}: {e}")
            return []
    
    async def get_shifts_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Shift]:
        """Получает смены в диапазоне дат."""
        try:
            query = select(Shift).where(
                and_(
                    Shift.start_time >= start_date,
                    Shift.start_time <= end_date
                )
            ).order_by(Shift.start_time.desc())
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting shifts by date range: {e}")
            return []
    
    async def update_shift(self, shift_id: int, update_data: Dict[str, Any]) -> bool:
        """Обновляет смену."""
        try:
            query = update(Shift).where(Shift.id == shift_id).values(**update_data)
            result = await self.db.execute(query)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Shift {shift_id} updated successfully")
                return True
            else:
                logger.warning(f"Shift {shift_id} not found for update")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Database error while updating shift {shift_id}: {e}")
            await self.db.rollback()
            return False
    
    async def close_shift(self, shift_id: int, end_time: datetime, end_coordinates: str) -> bool:
        """Закрывает смену."""
        try:
            shift = await self.get_shift(shift_id)
            if not shift:
                logger.error(f"Shift {shift_id} not found")
                return False
            
            if shift.status != 'active':
                logger.error(f"Shift {shift_id} is not active")
                return False
            
            # Вычисляем общее время и оплату
            duration = end_time - shift.start_time
            total_hours = duration.total_seconds() / 3600
            
            update_data = {
                'end_time': end_time,
                'end_coordinates': end_coordinates,
                'status': 'completed',
                'total_hours': total_hours,
                'total_payment': total_hours * shift.hourly_rate if shift.hourly_rate else None
            }
            
            return await self.update_shift(shift_id, update_data)
            
        except Exception as e:
            logger.error(f"Error while closing shift {shift_id}: {e}")
            return False
    
    async def get_shift_statistics(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получает статистику смен пользователя."""
        try:
            shifts = await self.get_shifts_by_date_range(start_date, end_date)
            user_shifts = [s for s in shifts if s.user_id == user_id and s.status == 'completed']
            
            total_hours = sum(s.total_hours or 0 for s in user_shifts)
            total_payment = sum(s.total_payment or 0 for s in user_shifts)
            total_shifts = len(user_shifts)
            
            return {
                'total_shifts': total_shifts,
                'total_hours': total_hours,
                'total_payment': total_payment,
                'average_hours_per_shift': total_hours / total_shifts if total_shifts > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error while getting shift statistics for user {user_id}: {e}")
            return {}
