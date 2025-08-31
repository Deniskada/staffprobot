"""Сервис управления тайм-слотами объектов."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from core.database.connection import get_sync_session
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object
from domain.entities.shift_schedule import ShiftSchedule
from core.logging.logger import logger


class TimeSlotService:
    """Сервис для управления тайм-слотами объектов."""
    
    def __init__(self):
        """Инициализация сервиса."""
        logger.info("TimeSlotService initialized")
    
    def create_default_time_slots(self, object_id: int, start_date: date, 
                                 end_date: date) -> List[TimeSlot]:
        """
        Создает стандартные тайм-слоты для объекта на период.
        
        Args:
            object_id: ID объекта
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список созданных тайм-слотов
        """
        try:
            with get_sync_session() as db:
                # Получаем объект
                obj = db.query(Object).filter(Object.id == object_id).first()
                if not obj:
                    logger.error(f"Object {object_id} not found")
                    return []
                
                created_slots = []
                current_date = start_date
                
                while current_date <= end_date:
                    # Создаем стандартный слот в рабочее время
                    default_slot = TimeSlot(
                        object_id=object_id,
                        slot_date=current_date,
                        start_time=obj.opening_time,
                        end_time=obj.closing_time,
                        hourly_rate=obj.hourly_rate,
                        max_employees=1,
                        is_additional=False,
                        is_active=True
                    )
                    
                    db.add(default_slot)
                    created_slots.append(default_slot)
                    
                    current_date += timedelta(days=1)
                
                db.commit()
                logger.info(f"Created {len(created_slots)} default time slots for object {object_id}")
                return created_slots
                
        except Exception as e:
            logger.error(f"Error creating default time slots: {e}")
            return []
    
    def create_additional_time_slot(self, object_id: int, slot_date: date,
                                   start_time: time, end_time: time,
                                   hourly_rate: Optional[float] = None,
                                   max_employees: int = 1,
                                   notes: Optional[str] = None) -> Optional[TimeSlot]:
        """
        Создает дополнительный тайм-слот.
        
        Args:
            object_id: ID объекта
            slot_date: Дата слота
            start_time: Время начала
            end_time: Время окончания
            hourly_rate: Часовая ставка (по умолчанию объекта)
            max_employees: Максимум сотрудников
            notes: Заметки
            
        Returns:
            Созданный тайм-слот или None
        """
        try:
            with get_sync_session() as db:
                # Получаем объект для ставки по умолчанию
                obj = db.query(Object).filter(Object.id == object_id).first()
                if not obj:
                    logger.error(f"Object {object_id} not found")
                    return None
                
                # Определяем ставку
                if hourly_rate is None:
                    hourly_rate = float(obj.hourly_rate)
                
                # Создаем слот
                time_slot = TimeSlot(
                    object_id=object_id,
                    slot_date=slot_date,
                    start_time=start_time,
                    end_time=end_time,
                    hourly_rate=hourly_rate,
                    max_employees=max_employees,
                    is_additional=True,
                    is_active=True,
                    notes=notes
                )
                
                db.add(time_slot)
                db.commit()
                
                logger.info(f"Created additional time slot for object {object_id}: {slot_date} {start_time}-{end_time}")
                return time_slot
                
        except Exception as e:
            logger.error(f"Error creating additional time slot: {e}")
            return None
    
    async def get_object_timeslots(self, object_id: int) -> List[Dict[str, Any]]:
        """
        Получает все тайм-слоты объекта.
        
        Args:
            object_id: ID объекта
            
        Returns:
            Список тайм-слотов в виде словарей
        """
        try:
            with get_sync_session() as db:
                timeslots = db.query(TimeSlot).filter(
                    TimeSlot.object_id == object_id
                ).order_by(TimeSlot.slot_date, TimeSlot.start_time).all()
                
                result = []
                for ts in timeslots:
                    result.append({
                        'id': ts.id,
                        'object_id': ts.object_id,
                        'slot_date': ts.slot_date,
                        'start_time': ts.start_time,
                        'end_time': ts.end_time,
                        'hourly_rate': float(ts.hourly_rate) if ts.hourly_rate else None,
                        'max_employees': ts.max_employees,
                        'is_additional': ts.is_additional,
                        'is_active': ts.is_active,
                        'notes': ts.notes,
                        'created_at': ts.created_at,
                        'updated_at': ts.updated_at
                    })
                
                logger.info(f"Retrieved {len(result)} timeslots for object {object_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error retrieving object timeslots: {e}")
            return []
    
    async def create_timeslot(self, object_id: int, slot_date: date,
                             start_time: time, end_time: time,
                             is_additional: bool = False,
                             hourly_rate: Optional[float] = None,
                             max_employees: int = 1,
                             notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Создает новый тайм-слот.
        
        Args:
            object_id: ID объекта
            slot_date: Дата слота
            start_time: Время начала
            end_time: Время окончания
            is_additional: Дополнительный слот
            hourly_rate: Часовая ставка
            max_employees: Максимум сотрудников
            notes: Заметки
            
        Returns:
            Результат создания
        """
        try:
            with get_sync_session() as db:
                # Получаем объект для ставки по умолчанию
                obj = db.query(Object).filter(Object.id == object_id).first()
                if not obj:
                    return {'success': False, 'error': 'Объект не найден'}
                
                # Определяем ставку
                if hourly_rate is None:
                    hourly_rate = float(obj.hourly_rate) if obj.hourly_rate else 0
                
                # Проверяем корректность времени
                if start_time >= end_time:
                    return {'success': False, 'error': 'Время начала должно быть меньше времени окончания'}
                
                # Создаем тайм-слот
                timeslot = TimeSlot(
                    object_id=object_id,
                    slot_date=slot_date,
                    start_time=start_time,
                    end_time=end_time,
                    hourly_rate=hourly_rate,
                    max_employees=max_employees,
                    is_additional=is_additional,
                    is_active=True,
                    notes=notes
                )
                
                db.add(timeslot)
                db.commit()
                
                logger.info(f"Created timeslot {timeslot.id} for object {object_id}")
                return {
                    'success': True,
                    'timeslot_id': timeslot.id,
                    'message': 'Тайм-слот успешно создан'
                }
                
        except Exception as e:
            logger.error(f"Error creating timeslot: {e}")
            return {'success': False, 'error': f'Ошибка создания тайм-слота: {str(e)}'}
    
    async def update_timeslot(self, timeslot_id: int, **kwargs) -> Dict[str, Any]:
        """
        Обновляет тайм-слот.
        
        Args:
            timeslot_id: ID тайм-слота
            **kwargs: Поля для обновления
            
        Returns:
            Результат обновления
        """
        try:
            with get_sync_session() as db:
                timeslot = db.query(TimeSlot).filter(TimeSlot.id == timeslot_id).first()
                if not timeslot:
                    return {'success': False, 'error': 'Тайм-слот не найден'}
                
                # Обновляем поля
                for field, value in kwargs.items():
                    if hasattr(timeslot, field):
                        setattr(timeslot, field, value)
                
                timeslot.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Updated timeslot {timeslot_id}")
                return {
                    'success': True,
                    'message': 'Тайм-слот успешно обновлен'
                }
                
        except Exception as e:
            logger.error(f"Error updating timeslot: {e}")
            return {'success': False, 'error': f'Ошибка обновления: {str(e)}'}
    
    async def delete_timeslot(self, timeslot_id: int) -> Dict[str, Any]:
        """
        Удаляет тайм-слот.
        
        Args:
            timeslot_id: ID тайм-слота
            
        Returns:
            Результат удаления
        """
        try:
            with get_sync_session() as db:
                timeslot = db.query(TimeSlot).filter(TimeSlot.id == timeslot_id).first()
                if not timeslot:
                    return {'success': False, 'error': 'Тайм-слот не найден'}
                
                # Проверяем, есть ли запланированные смены
                scheduled_shifts = db.query(ShiftSchedule).filter(
                    ShiftSchedule.timeslot_id == timeslot_id
                ).count()
                
                if scheduled_shifts > 0:
                    return {'success': False, 'error': 'Нельзя удалить тайм-слот с запланированными сменами'}
                
                db.delete(timeslot)
                db.commit()
                
                logger.info(f"Deleted timeslot {timeslot_id}")
                return {
                    'success': True,
                    'message': 'Тайм-слот успешно удален'
                }
                
        except Exception as e:
            logger.error(f"Error deleting timeslot: {e}")
            return {'success': False, 'error': f'Ошибка удаления: {str(e)}'}
    
    def get_available_time_slots(self, object_id: int, target_date: date) -> List[Dict[str, Any]]:
        """
        Получает доступные тайм-слоты для объекта на дату.
        
        Args:
            object_id: ID объекта
            target_date: Целевая дата
            
        Returns:
            Список доступных слотов с информацией о занятости
        """
        try:
            with get_sync_session() as db:
                # Получаем все тайм-слоты на дату
                time_slots = db.query(TimeSlot).filter(
                    and_(
                        TimeSlot.object_id == object_id,
                        TimeSlot.slot_date == target_date,
                        TimeSlot.is_active == True
                    )
                ).all()
                
                if not time_slots:
                    return []
                
                # Получаем забронированные смены на эту дату
                booked_schedules = db.query(ShiftSchedule).filter(
                    and_(
                        ShiftSchedule.object_id == object_id,
                        func.date(ShiftSchedule.planned_start) == target_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                ).all()
                
                available_slots = []
                
                for slot in time_slots:
                    # Получаем доступные интервалы в слоте
                    available_intervals = slot.get_available_intervals(booked_schedules)
                    
                    if available_intervals:
                        available_slots.append({
                            "id": slot.id,
                            "start_time": slot.start_time,
                            "end_time": slot.end_time,
                            "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else None,
                            "max_employees": slot.max_employees,
                            "is_additional": slot.is_additional,
                            "notes": slot.notes,
                            "available_intervals": available_intervals,
                            "total_duration": slot.duration_hours
                        })
                
                return available_slots
                
        except Exception as e:
            logger.error(f"Error getting available time slots: {e}")
            return []
    
    def book_time_slot(self, user_id: int, time_slot_id: int,
                       start_time: time, end_time: time) -> Optional[ShiftSchedule]:
        """
        Бронирует тайм-слот для сотрудника.
        
        Args:
            user_id: ID сотрудника
            time_slot_id: ID тайм-слота
            start_time: Время начала работы
            end_time: Время окончания работы
            
        Returns:
            Созданная запланированная смена или None
        """
        try:
            with get_sync_session() as db:
                # Получаем тайм-слот
                time_slot = db.query(TimeSlot).filter(TimeSlot.id == time_slot_id).first()
                if not time_slot:
                    logger.error(f"Time slot {time_slot_id} not found")
                    return None
                
                # Проверяем доступность
                booked_schedules = db.query(ShiftSchedule).filter(
                    and_(
                        ShiftSchedule.object_id == time_slot.object_id,
                        func.date(ShiftSchedule.planned_start) == time_slot.slot_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                ).all()
                
                if not time_slot.can_accommodate_employee(start_time, end_time, booked_schedules):
                    logger.warning(f"Time slot {time_slot_id} cannot accommodate employee at {start_time}-{end_time}")
                    return None
                
                # Создаем запланированную смену
                shift_schedule = ShiftSchedule(
                    user_id=user_id,
                    object_id=time_slot.object_id,
                    planned_start=datetime.combine(time_slot.slot_date, start_time),
                    planned_end=datetime.combine(time_slot.slot_date, end_time),
                    status="planned",
                    hourly_rate=time_slot.hourly_rate
                )
                
                db.add(shift_schedule)
                db.commit()
                
                logger.info(f"Booked time slot {time_slot_id} for user {user_id}: {start_time}-{end_time}")
                return shift_schedule
                
        except Exception as e:
            logger.error(f"Error booking time slot: {e}")
            return None
    
    def update_time_slot(self, time_slot_id: int, **kwargs) -> bool:
        """
        Обновляет тайм-слот.
        
        Args:
            time_slot_id: ID тайм-слота
            **kwargs: Поля для обновления
            
        Returns:
            True если успешно обновлен
        """
        try:
            with get_sync_session() as db:
                time_slot = db.query(TimeSlot).filter(TimeSlot.id == time_slot_id).first()
                if not time_slot:
                    logger.error(f"Time slot {time_slot_id} not found")
                    return False
                
                # Обновляем поля
                for key, value in kwargs.items():
                    if hasattr(time_slot, key):
                        setattr(time_slot, key, value)
                
                db.commit()
                logger.info(f"Updated time slot {time_slot_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating time slot: {e}")
            return False
    
    def delete_time_slot(self, time_slot_id: int) -> bool:
        """
        Удаляет тайм-слот.
        
        Args:
            time_slot_id: ID тайм-слота
            
        Returns:
            True если успешно удален
        """
        try:
            with get_sync_session() as db:
                time_slot = db.query(TimeSlot).filter(TimeSlot.id == time_slot_id).first()
                if not time_slot:
                    logger.error(f"Time slot {time_slot_id} not found")
                    return False
                
                # Проверяем, есть ли забронированные смены
                booked_count = db.query(ShiftSchedule).filter(
                    and_(
                        ShiftSchedule.object_id == time_slot.object_id,
                        func.date(ShiftSchedule.planned_start) == time_slot.slot_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                ).count()
                
                if booked_count > 0:
                    logger.warning(f"Cannot delete time slot {time_slot_id}: {booked_count} booked schedules")
                    return False
                
                db.delete(time_slot)
                db.commit()
                
                logger.info(f"Deleted time slot {time_slot_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting time slot: {e}")
            return False
    
    async def auto_close_expired_shifts(self) -> Dict[str, Any]:
        """Автоматически закрывает просроченные смены."""
        try:
            now = datetime.now()
            
            with get_sync_session() as db:
                # Получаем все активные смены, которые должны быть закрыты
                expired_shifts = db.query(ShiftSchedule).join(Object).filter(
                    and_(
                        ShiftSchedule.status == 'active',
                        ShiftSchedule.end_time < now
                    )
                ).all()
                
                closed_count = 0
                errors = []
                
                for shift in expired_shifts:
                    try:
                        # Проверяем, прошло ли достаточно времени для авто-закрытия
                        object_auto_close_minutes = getattr(shift.object, 'auto_close_minutes', 60)
                        time_since_end = now - shift.end_time
                        
                        if time_since_end.total_seconds() / 60 >= object_auto_close_minutes:
                            # Закрываем смену
                            shift.status = 'completed'
                            shift.actual_end_time = now
                            # Добавляем поле auto_closed если его нет
                            if not hasattr(shift, 'auto_closed'):
                                shift.auto_closed = True
                            
                            closed_count += 1
                            logger.info(f"Auto-closed expired shift {shift.id} for user {shift.user_id}")
                        else:
                            logger.debug(f"Shift {shift.id} not ready for auto-close yet")
                            
                    except Exception as e:
                        error_msg = f"Error auto-closing shift {shift.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # Сохраняем изменения
                db.commit()
                
                return {
                    "success": True,
                    "closed_count": closed_count,
                    "errors": errors
                }
                
        except Exception as e:
            logger.error(f"Error in auto_close_expired_shifts: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_expired_shifts_count(self) -> int:
        """Получает количество просроченных смен для мониторинга."""
        try:
            now = datetime.now()
            with get_sync_session() as db:
                expired_shifts = db.query(ShiftSchedule).join(Object).filter(
                    and_(
                        ShiftSchedule.status == 'active',
                        ShiftSchedule.end_time < now
                    )
                ).all()
                return len(expired_shifts)
        except Exception as e:
            logger.error(f"Error getting expired shifts count: {e}")
            return 0
    
    def get_object_time_slots(self, object_id: int, start_date: date, 
                             end_date: date) -> List[TimeSlot]:
        """
        Получает все тайм-слоты объекта за период.
        
        Args:
            object_id: ID объекта
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список тайм-слотов
        """
        try:
            with get_sync_session() as db:
                time_slots = db.query(TimeSlot).filter(
                    and_(
                        TimeSlot.object_id == object_id,
                        TimeSlot.slot_date >= start_date,
                        TimeSlot.slot_date <= end_date,
                        TimeSlot.is_active == True
                    )
                ).order_by(TimeSlot.slot_date, TimeSlot.start_time).all()
                
                return time_slots
                
        except Exception as e:
            logger.error(f"Error getting object time slots: {e}")
            return []
