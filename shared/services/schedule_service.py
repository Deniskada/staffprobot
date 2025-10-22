"""Общий сервис для планирования смен с интеграцией тайм-слотов."""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, time, timezone, date
from core.logging.logger import logger
from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.time_slot import TimeSlot
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload
from .base_service import BaseService


class ScheduleService(BaseService):
    """Общий сервис для планирования смен с интеграцией тайм-слотов."""
    
    def _initialize_service(self):
        """Инициализация сервиса."""
        logger.info("Shared ScheduleService initialized")
    
    async def get_available_time_slots_for_date(
        self, 
        object_id: int, 
        target_date: date
    ) -> Dict[str, Any]:
        """
        Получает доступные тайм-слоты для объекта на дату.
        
        Args:
            object_id: ID объекта
            target_date: Целевая дата
            
        Returns:
            Словарь с доступными тайм-слотами
        """
        try:
            async with get_async_session() as session:
                # Получаем объект
                object_query = select(Object).where(Object.id == object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }
                
                # Получаем тайм-слоты для даты
                time_slots_query = select(TimeSlot).where(
                    and_(
                        TimeSlot.object_id == object_id,
                        TimeSlot.slot_date == target_date,
                        TimeSlot.is_active == True
                    )
                ).order_by(TimeSlot.start_time)
                
                time_slots_result = await session.execute(time_slots_query)
                time_slots = time_slots_result.scalars().all()
                
                # Получаем запланированные смены для даты
                shifts_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.object_id == object_id,
                        func.date(ShiftSchedule.planned_start) == target_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                )
                
                shifts_result = await session.execute(shifts_query)
                shifts = shifts_result.scalars().all()
                
                # Формируем список доступных тайм-слотов
                available_slots = []
                for slot in time_slots:
                    # Считаем количество запланированных смен в этом тайм-слоте
                    scheduled_count = sum(
                        1 for shift in shifts 
                        if shift.time_slot_id == slot.id
                    )
                    
                    # Проверяем доступность: текущая занятость < максимального количества
                    is_available = scheduled_count < slot.max_employees
                    
                    if is_available:
                        # Формируем информацию о занятости
                        availability = f"{scheduled_count}/{slot.max_employees}"
                        
                        available_slots.append({
                            'id': slot.id,
                            'start_time': slot.start_time.strftime('%H:%M'),
                            'end_time': slot.end_time.strftime('%H:%M'),
                            'hourly_rate': float(slot.hourly_rate) if slot.hourly_rate else None,
                            'description': slot.notes or '',
                            'max_employees': slot.max_employees,
                            'availability': availability,
                            'scheduled_count': scheduled_count
                        })
                
                return {
                    'success': True,
                    'object_name': obj.name,
                    'date': target_date.isoformat(),
                    'available_slots': available_slots,
                    'total_slots': len(available_slots)
                }
                
        except Exception as e:
            logger.error(f"Error getting time slots for date: {e}")
            return {
                'success': False,
                'error': f'Ошибка получения тайм-слотов: {str(e)}'
            }
    
    async def create_scheduled_shift_from_timeslot(
        self,
        user_id: int,
        time_slot_id: int,
        start_time,
        end_time,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает запланированную смену из тайм-слота.
        
        Args:
            user_id: Telegram ID пользователя
            time_slot_id: ID тайм-слота
            start_time: Время начала смены
            end_time: Время окончания смены
            notes: Дополнительные заметки
            
        Returns:
            Результат создания смены
        """
        try:
            async with get_async_session() as session:
                # Получаем пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден'
                    }
                
                # Получаем тайм-слот
                time_slot_query = select(TimeSlot).where(TimeSlot.id == time_slot_id)
                time_slot_result = await session.execute(time_slot_query)
                time_slot = time_slot_result.scalar_one_or_none()
                
                if not time_slot:
                    return {
                        'success': False,
                        'error': 'Тайм-слот не найден'
                    }
                
                # Проверяем доступность тайм-слота
                if not time_slot.is_active:
                    return {
                        'success': False,
                        'error': 'Тайм-слот недоступен'
                    }
                
                # Проверяем доступность тайм-слота (учитываем max_employees)
                existing_shifts_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.time_slot_id == time_slot_id,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                )
                existing_shifts_result = await session.execute(existing_shifts_query)
                existing_shifts = existing_shifts_result.scalars().all()
                
                # Считаем количество запланированных смен
                scheduled_count = len(existing_shifts)
                
                # Проверяем, есть ли свободные места
                if scheduled_count >= time_slot.max_employees:
                    return {
                        'success': False,
                        'error': f'Тайм-слот полностью занят ({scheduled_count}/{time_slot.max_employees})'
                    }
                
                # Получаем объект для timezone
                object_query = select(Object).where(Object.id == time_slot.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }
                
                # Конвертируем локальное время объекта в UTC для корректного хранения
                import pytz
                object_timezone = obj.timezone if obj.timezone else 'Europe/Moscow'
                tz = pytz.timezone(object_timezone)
                
                # Создаём naive datetime в локальном времени объекта
                start_datetime_naive = datetime.combine(time_slot.slot_date, start_time)
                end_datetime_naive = datetime.combine(time_slot.slot_date, end_time)
                
                # Локализуем в timezone объекта, затем конвертируем в UTC для сохранения
                start_datetime = tz.localize(start_datetime_naive).astimezone(pytz.UTC).replace(tzinfo=None)
                end_datetime = tz.localize(end_datetime_naive).astimezone(pytz.UTC).replace(tzinfo=None)
                
                logger.info(
                    f"Timezone conversion for bot scheduling (shared)",
                    timezone=object_timezone,
                    local_start=start_datetime_naive.isoformat(),
                    utc_start=start_datetime.isoformat()
                )
                
                # Создаем смену
                new_shift = ShiftSchedule(
                    user_id=user.id,
                    object_id=time_slot.object_id,
                    time_slot_id=time_slot_id,
                    planned_start=start_datetime,
                    planned_end=end_datetime,
                    hourly_rate=time_slot.hourly_rate,
                    status="planned",
                    notes=notes
                )
                
                session.add(new_shift)
                await session.commit()
                await session.refresh(new_shift)
                
                logger.info(
                    f"Scheduled shift created from timeslot: user_id={user_id}, shift_id={new_shift.id}, time_slot_id={time_slot_id}, object_id={time_slot.object_id}"
                )
                
                return {
                    'success': True,
                    'shift_id': new_shift.id,
                    'start_time': time_slot.start_time.strftime("%H:%M"),
                    'end_time': time_slot.end_time.strftime("%H:%M"),
                    'hourly_rate': float(time_slot.hourly_rate) if time_slot.hourly_rate else 0,
                    'message': f'Смена запланирована на {time_slot.slot_date.strftime("%d.%m.%Y")} с {time_slot.start_time.strftime("%H:%M")} до {time_slot.end_time.strftime("%H:%M")}'
                }
                
        except Exception as e:
            logger.error(f"Error creating scheduled shift from timeslot: {e}")
            return {
                'success': False,
                'error': f'Ошибка создания смены: {str(e)}'
            }
    
    async def get_user_scheduled_shifts(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Получает запланированные смены пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            
        Returns:
            Список запланированных смен
        """
        try:
            async with get_async_session() as session:
                # Получаем пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден'
                    }
                
                # Строим запрос
                shifts_query = select(Shift).options(
                    joinedload(Shift.object),
                    joinedload(Shift.time_slot)
                ).where(
                    and_(
                        Shift.user_id == user.id,
                        Shift.status == "scheduled"
                    )
                )
                
                # Добавляем фильтры по дате если указаны
                if start_date:
                    shifts_query = shifts_query.where(
                        func.date(Shift.start_time) >= start_date
                    )
                
                if end_date:
                    shifts_query = shifts_query.where(
                        func.date(Shift.start_time) <= end_date
                    )
                
                shifts_query = shifts_query.order_by(Shift.start_time)
                
                shifts_result = await session.execute(shifts_query)
                shifts = shifts_result.scalars().all()
                
                # Формируем список смен
                scheduled_shifts = []
                for shift in shifts:
                    scheduled_shifts.append({
                        'id': shift.id,
                        'object_name': shift.object.name,
                        'date': shift.start_time.date().isoformat(),
                        'start_time': shift.start_time.strftime('%H:%M'),
                        'end_time': shift.end_time.strftime('%H:%M'),
                        'hourly_rate': float(shift.hourly_rate) if shift.hourly_rate else None,
                        'status': shift.status,
                        'notes': shift.notes or '',
                        'time_slot_id': shift.time_slot_id
                    })
                
                return {
                    'success': True,
                    'shifts': scheduled_shifts,
                    'total': len(scheduled_shifts)
                }
                
        except Exception as e:
            logger.error(f"Error getting user scheduled shifts: {e}")
            return {
                'success': False,
                'error': f'Ошибка получения смен: {str(e)}'
            }
    
    async def cancel_scheduled_shift(
        self,
        user_id: int,
        shift_id: int
    ) -> Dict[str, Any]:
        """
        Отменяет запланированную смену.
        
        Args:
            user_id: Telegram ID пользователя
            shift_id: ID смены
            
        Returns:
            Результат отмены смены
        """
        try:
            async with get_async_session() as session:
                # Получаем пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден'
                    }
                
                # Получаем смену
                shift_query = select(Shift).where(
                    and_(
                        Shift.id == shift_id,
                        Shift.user_id == user.id,
                        Shift.status == "scheduled"
                    )
                )
                shift_result = await session.execute(shift_query)
                shift = shift_result.scalar_one_or_none()
                
                if not shift:
                    return {
                        'success': False,
                        'error': 'Смена не найдена или уже не запланирована'
                    }
                
                # Отменяем смену
                shift.status = "cancelled"
                await session.commit()
                
                logger.info(
                    f"Scheduled shift cancelled",
                    user_id=user_id,
                    shift_id=shift_id
                )
                
                return {
                    'success': True,
                    'message': 'Смена успешно отменена'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling scheduled shift: {e}")
            return {
                'success': False,
                'error': f'Ошибка отмены смены: {str(e)}'
            }


