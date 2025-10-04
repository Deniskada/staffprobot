"""Сервис для работы с запланированными сменами в боте."""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object
from domain.entities.user import User
from sqlalchemy import select, and_


class ShiftScheduleService:
    """Сервис для работы с запланированными сменами."""
    
    def __init__(self):
        logger.info("ShiftScheduleService initialized")
    
    async def get_user_planned_shifts_for_date(self, user_telegram_id: int, target_date: date) -> List[Dict[str, Any]]:
        """
        Получает запланированные смены пользователя на указанную дату.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            target_date: Дата для поиска смен
            
        Returns:
            Список запланированных смен
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == user_telegram_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User with telegram_id {user_telegram_id} not found")
                    return []
                
                # Получаем запланированные смены пользователя на указанную дату
                query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.user_id == user.id,
                        ShiftSchedule.status.in_(["planned", "confirmed"]),
                        ShiftSchedule.planned_start >= datetime.combine(target_date, datetime.min.time()),
                        ShiftSchedule.planned_start < datetime.combine(target_date, datetime.min.time()) + timedelta(days=1)
                    )
                ).order_by(ShiftSchedule.planned_start)
                
                result = await session.execute(query)
                shifts = result.scalars().all()
                
                # Получаем информацию об объектах и тайм-слотах
                planned_shifts = []
                for shift in shifts:
                    # Получаем информацию об объекте
                    object_query = select(Object).where(Object.id == shift.object_id)
                    object_result = await session.execute(object_query)
                    obj = object_result.scalar_one_or_none()
                    
                    # Получаем информацию о тайм-слоте
                    timeslot_query = select(TimeSlot).where(TimeSlot.id == shift.time_slot_id)
                    timeslot_result = await session.execute(timeslot_query)
                    timeslot = timeslot_result.scalar_one_or_none()
                    
                    planned_shifts.append({
                        'id': shift.id,
                        'user_id': shift.user_id,
                        'object_id': shift.object_id,
                        'object_name': obj.name if obj else 'Неизвестно',
                        'object_timezone': obj.timezone if obj else 'Europe/Moscow',
                        'time_slot_id': shift.time_slot_id,
                        'planned_start': shift.planned_start,
                        'planned_end': shift.planned_end,
                        'status': shift.status,
                        'hourly_rate': shift.hourly_rate,
                        'notes': shift.notes,
                        'timeslot_start': timeslot.start_time if timeslot else None,
                        'timeslot_end': timeslot.end_time if timeslot else None
                    })
                
                logger.info(f"Found {len(planned_shifts)} planned shifts for user {user_telegram_id} on {target_date}")
                return planned_shifts
                
        except Exception as e:
            logger.error(f"Error getting planned shifts for user {user_telegram_id} on {target_date}: {e}")
            return []
    
    
    async def get_shift_schedule_by_id(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о запланированной смене по ID.
        
        Args:
            schedule_id: ID запланированной смены
            
        Returns:
            Информация о запланированной смене или None
        """
        try:
            logger.info(f"Getting shift schedule by ID: {schedule_id}")
            async with get_async_session() as session:
                query = select(ShiftSchedule).where(ShiftSchedule.id == schedule_id)
                result = await session.execute(query)
                shift = result.scalar_one_or_none()
                
                if not shift:
                    logger.warning(f"Shift schedule with ID {schedule_id} not found")
                    return None
                
                # Получаем информацию об объекте
                object_query = select(Object).where(Object.id == shift.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                logger.info(f"Found object: {obj.name if obj else 'None'}")
                
                # Получаем информацию о тайм-слоте
                timeslot_query = select(TimeSlot).where(TimeSlot.id == shift.time_slot_id)
                timeslot_result = await session.execute(timeslot_query)
                timeslot = timeslot_result.scalar_one_or_none()
                
                logger.info(f"Found timeslot: {timeslot.start_time if timeslot else 'None'}")
                
                result = {
                    'id': shift.id,
                    'user_id': shift.user_id,
                    'object_id': shift.object_id,
                    'object_name': obj.name if obj else 'Неизвестно',
                    'time_slot_id': shift.time_slot_id,
                    'planned_start': shift.planned_start,
                    'planned_end': shift.planned_end,
                    'status': shift.status,
                    'hourly_rate': shift.hourly_rate,
                    'notes': shift.notes,
                    'timeslot_start': timeslot.start_time if timeslot else None,
                    'timeslot_end': timeslot.end_time if timeslot else None
                }
                
                logger.info(f"Returning shift data: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Error getting shift schedule {schedule_id}: {e}")
            return None
