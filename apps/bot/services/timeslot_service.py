"""Сервис для работы с тайм-слотами в боте."""

from typing import List, Dict, Any, Optional
from datetime import date, datetime
from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.time_slot import TimeSlot
from domain.entities.shift_schedule import ShiftSchedule
from sqlalchemy import select, and_


class TimeSlotService:
    """Сервис для работы с тайм-слотами."""
    
    def __init__(self):
        logger.info("TimeSlotService initialized")
    
    async def get_available_timeslots_for_object(self, object_id: int, target_date: date) -> List[Dict[str, Any]]:
        """
        Получает доступные тайм-слоты для объекта на указанную дату.
        
        Args:
            object_id: ID объекта
            target_date: Дата для поиска тайм-слотов
            
        Returns:
            Список доступных тайм-слотов
        """
        try:
            async with get_async_session() as session:
                # Получаем активные тайм-слоты для объекта на указанную дату
                query = select(TimeSlot).where(
                    and_(
                        TimeSlot.object_id == object_id,
                        TimeSlot.slot_date == target_date,
                        TimeSlot.is_active == True
                    )
                ).order_by(TimeSlot.start_time)
                
                result = await session.execute(query)
                timeslots = result.scalars().all()
                
                # Получаем запланированные смены для этих тайм-слотов
                timeslot_ids = [ts.id for ts in timeslots]
                scheduled_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.time_slot_id.in_(timeslot_ids),
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                )
                scheduled_result = await session.execute(scheduled_query)
                scheduled_shifts = scheduled_result.scalars().all()
                
                # Группируем смены по тайм-слотам
                scheduled_by_timeslot = {}
                for shift in scheduled_shifts:
                    if shift.time_slot_id not in scheduled_by_timeslot:
                        scheduled_by_timeslot[shift.time_slot_id] = []
                    scheduled_by_timeslot[shift.time_slot_id].append(shift)
                
                # Формируем список доступных тайм-слотов
                available_timeslots = []
                for timeslot in timeslots:
                    scheduled_count = len(scheduled_by_timeslot.get(timeslot.id, []))
                    
                    # Тайм-слот доступен, если есть свободные места
                    if scheduled_count < timeslot.max_employees:
                        available_timeslots.append({
                            'id': timeslot.id,
                            'object_id': timeslot.object_id,
                            'slot_date': timeslot.slot_date,
                            'start_time': timeslot.start_time,
                            'end_time': timeslot.end_time,
                            'hourly_rate': timeslot.hourly_rate,
                            'max_employees': timeslot.max_employees,
                            'scheduled_count': scheduled_count,
                            'available_spots': timeslot.max_employees - scheduled_count
                        })
                
                logger.info(f"Found {len(available_timeslots)} available timeslots for object {object_id} on {target_date}")
                return available_timeslots
                
        except Exception as e:
            logger.error(f"Error getting available timeslots for object {object_id} on {target_date}: {e}")
            return []
    
    async def get_timeslot_by_id(self, timeslot_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о тайм-слоте по ID.
        
        Args:
            timeslot_id: ID тайм-слота
            
        Returns:
            Информация о тайм-слоте или None
        """
        try:
            async with get_async_session() as session:
                query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
                result = await session.execute(query)
                timeslot = result.scalar_one_or_none()
                
                if not timeslot:
                    return None
                
                # Получаем информацию об объекте
                from domain.entities.object import Object
                object_query = select(Object).where(Object.id == timeslot.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                return {
                    'id': timeslot.id,
                    'object_id': timeslot.object_id,
                    'object_name': obj.name if obj else 'Неизвестно',
                    'slot_date': timeslot.slot_date,
                    'start_time': timeslot.start_time,
                    'end_time': timeslot.end_time,
                    'hourly_rate': timeslot.hourly_rate,
                    'max_employees': timeslot.max_employees,
                    'notes': timeslot.notes
                }
                
        except Exception as e:
            logger.error(f"Error getting timeslot {timeslot_id}: {e}")
            return None
