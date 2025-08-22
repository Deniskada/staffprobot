"""Сервис для планирования смен."""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, time, timezone
from core.logging.logger import logger
from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.user import User
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload


class ScheduleService:
    """Сервис для планирования смен."""
    
    def __init__(self):
        """Инициализация сервиса."""
        logger.info("ScheduleService initialized")
    
    async def create_scheduled_shift(
        self,
        user_id: int,  # telegram_id
        object_id: int,
        planned_start: datetime,
        planned_end: datetime,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает запланированную смену.
        
        Args:
            user_id: telegram_id пользователя
            object_id: ID объекта
            planned_start: Планируемое время начала
            planned_end: Планируемое время окончания
            notes: Заметки к смене
            
        Returns:
            Результат создания запланированной смены
        """
        try:
            logger.info(
                f"Creating scheduled shift: user_id={user_id}, object_id={object_id}, "
                f"start={planned_start}, end={planned_end}"
            )
            
            async with get_async_session() as session:
                # Находим пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден'
                    }
                
                # Проверяем существование объекта
                obj_query = select(Object).where(Object.id == object_id)
                obj_result = await session.execute(obj_query)
                obj = obj_result.scalar_one_or_none()
                
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }
                
                # Проверяем доступность времени
                availability_check = await self._check_time_availability(
                    session, db_user.id, object_id, planned_start, planned_end
                )
                
                if not availability_check['available']:
                    return {
                        'success': False,
                        'error': availability_check['error'],
                        'conflicts': availability_check.get('conflicts', [])
                    }
                
                # Проверяем соответствие рабочему времени объекта
                time_check = self._check_working_hours(obj, planned_start, planned_end)
                if not time_check['valid']:
                    return {
                        'success': False,
                        'error': time_check['error']
                    }
                
                # Создаем запланированную смену
                scheduled_shift = ShiftSchedule(
                    user_id=db_user.id,
                    object_id=object_id,
                    planned_start=planned_start,
                    planned_end=planned_end,
                    hourly_rate=obj.hourly_rate,
                    notes=notes,
                    status='planned'
                )
                
                session.add(scheduled_shift)
                await session.commit()
                await session.refresh(scheduled_shift)
                
                logger.info(f"Scheduled shift created successfully: id={scheduled_shift.id}")
                
                return {
                    'success': True,
                    'schedule_id': scheduled_shift.id,
                    'message': f'Смена запланирована на {scheduled_shift.formatted_time_range}',
                    'planned_duration': scheduled_shift.planned_duration_hours,
                    'planned_payment': scheduled_shift.planned_payment,
                    'object_name': obj.name
                }
                
        except Exception as e:
            logger.error(f"Error creating scheduled shift: {e}")
            return {
                'success': False,
                'error': f'Ошибка при создании запланированной смены: {str(e)}'
            }
    
    async def _check_time_availability(
        self,
        session,
        user_id: int,  # db user_id, не telegram_id
        object_id: int,
        planned_start: datetime,
        planned_end: datetime,
        exclude_schedule_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Проверяет доступность времени для планирования.
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя в БД
            object_id: ID объекта
            planned_start: Планируемое время начала
            planned_end: Планируемое время окончания
            exclude_schedule_id: ID исключаемого расписания (для редактирования)
            
        Returns:
            Результат проверки доступности
        """
        conflicts = []
        
        try:
            # Проверяем конфликты с запланированными сменами пользователя
            schedule_query = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.user_id == user_id,
                    ShiftSchedule.status.in_(['planned', 'confirmed']),
                    or_(
                        and_(
                            ShiftSchedule.planned_start <= planned_start,
                            ShiftSchedule.planned_end > planned_start
                        ),
                        and_(
                            ShiftSchedule.planned_start < planned_end,
                            ShiftSchedule.planned_end >= planned_end
                        ),
                        and_(
                            ShiftSchedule.planned_start >= planned_start,
                            ShiftSchedule.planned_end <= planned_end
                        )
                    )
                )
            )
            
            if exclude_schedule_id:
                schedule_query = schedule_query.where(ShiftSchedule.id != exclude_schedule_id)
            
            schedule_result = await session.execute(schedule_query)
            conflicting_schedules = schedule_result.scalars().all()
            
            for schedule in conflicting_schedules:
                conflicts.append({
                    'type': 'scheduled_shift',
                    'time_range': schedule.formatted_time_range,
                    'object_id': schedule.object_id
                })
            
            # Проверяем конфликты с активными сменами пользователя
            shift_query = select(Shift).where(
                and_(
                    Shift.user_id == user_id,
                    Shift.status == 'active',
                    or_(
                        and_(
                            Shift.start_time <= planned_start,
                            Shift.end_time.is_(None)  # Активная смена без времени окончания
                        ),
                        and_(
                            Shift.start_time <= planned_start,
                            Shift.end_time > planned_start
                        ),
                        and_(
                            Shift.start_time < planned_end,
                            or_(
                                Shift.end_time >= planned_end,
                                Shift.end_time.is_(None)
                            )
                        )
                    )
                )
            )
            
            shift_result = await session.execute(shift_query)
            conflicting_shifts = shift_result.scalars().all()
            
            for shift in conflicting_shifts:
                end_time_str = shift.end_time.strftime('%H:%M') if shift.end_time else 'активна'
                conflicts.append({
                    'type': 'active_shift',
                    'time_range': f"{shift.start_time.strftime('%d.%m.%Y %H:%M')}-{end_time_str}",
                    'object_id': shift.object_id
                })
            
            if conflicts:
                return {
                    'available': False,
                    'error': 'Обнаружены конфликты с существующими сменами',
                    'conflicts': conflicts
                }
            
            return {'available': True}
            
        except Exception as e:
            logger.error(f"Error checking time availability: {e}")
            return {
                'available': False,
                'error': f'Ошибка при проверке доступности времени: {str(e)}'
            }
    
    def _check_working_hours(
        self,
        obj: Object,
        planned_start: datetime,
        planned_end: datetime
    ) -> Dict[str, Any]:
        """
        Проверяет соответствие рабочему времени объекта.
        
        Args:
            obj: Объект
            planned_start: Планируемое время начала (UTC)
            planned_end: Планируемое время окончания (UTC)
            
        Returns:
            Результат проверки
        """
        try:
            from core.utils.timezone_helper import timezone_helper
            
            # Конвертируем UTC время в локальное для сравнения с рабочим временем объекта
            local_start = timezone_helper.utc_to_local(planned_start)
            local_end = timezone_helper.utc_to_local(planned_end)
            
            start_time = local_start.time()
            end_time = local_end.time()
            
            # Проверяем, что смена начинается не раньше времени открытия
            if start_time < obj.opening_time:
                return {
                    'valid': False,
                    'error': f'Смена не может начинаться раньше {obj.opening_time.strftime("%H:%M")}'
                }
            
            # Проверяем, что смена заканчивается не позже времени закрытия
            if end_time > obj.closing_time:
                return {
                    'valid': False,
                    'error': f'Смена не может заканчиваться позже {obj.closing_time.strftime("%H:%M")}'
                }
            
            # Проверяем, что время начала раньше времени окончания
            if local_start >= local_end:
                return {
                    'valid': False,
                    'error': 'Время начала должно быть раньше времени окончания'
                }
            
            # Проверяем минимальную длительность смены (1 час)
            duration = planned_end - planned_start
            if duration < timedelta(hours=1):
                return {
                    'valid': False,
                    'error': 'Минимальная длительность смены - 1 час'
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error checking working hours: {e}")
            return {
                'valid': False,
                'error': f'Ошибка при проверке рабочего времени: {str(e)}'
            }
    
    async def get_user_scheduled_shifts(
        self,
        user_id: int,  # telegram_id
        status_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает запланированные смены пользователя.
        
        Args:
            user_id: telegram_id пользователя
            status_filter: Фильтр по статусу ('planned', 'confirmed', 'cancelled', 'completed')
            date_from: Начальная дата фильтра
            date_to: Конечная дата фильтра
            
        Returns:
            Список запланированных смен
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return []
                
                # Строим запрос для получения запланированных смен
                query = select(ShiftSchedule).options(
                    joinedload(ShiftSchedule.object)
                ).where(ShiftSchedule.user_id == db_user.id)
                
                if status_filter:
                    query = query.where(ShiftSchedule.status == status_filter)
                
                if date_from:
                    query = query.where(ShiftSchedule.planned_start >= date_from)
                
                if date_to:
                    query = query.where(ShiftSchedule.planned_end <= date_to)
                
                query = query.order_by(ShiftSchedule.planned_start)
                
                result = await session.execute(query)
                schedules = result.scalars().all()
                
                # Преобразуем в словари
                schedules_list = []
                for schedule in schedules:
                    schedules_list.append({
                        'id': schedule.id,
                        'object_id': schedule.object_id,
                        'object_name': schedule.object.name if schedule.object else 'Неизвестный объект',
                        'planned_start': schedule.planned_start,
                        'planned_end': schedule.planned_end,
                        'status': schedule.status,
                        'formatted_time_range': schedule.formatted_time_range,
                        'planned_duration_hours': schedule.planned_duration_hours,
                        'planned_payment': schedule.planned_payment,
                        'notes': schedule.notes,
                        'is_upcoming': schedule.is_upcoming,
                        'is_today': schedule.is_today,
                        'can_be_cancelled': schedule.can_be_cancelled(),
                        'needs_reminder': schedule.needs_reminder(),
                        'created_at': schedule.created_at
                    })
                
                logger.info(f"Retrieved {len(schedules_list)} scheduled shifts for user {user_id}")
                return schedules_list
                
        except Exception as e:
            logger.error(f"Error retrieving scheduled shifts: {e}")
            return []
    
    async def cancel_scheduled_shift(
        self,
        user_id: int,  # telegram_id
        schedule_id: int
    ) -> Dict[str, Any]:
        """
        Отменяет запланированную смену.
        
        Args:
            user_id: telegram_id пользователя
            schedule_id: ID запланированной смены
            
        Returns:
            Результат отмены
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден'
                    }
                
                # Находим запланированную смену
                schedule_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.id == schedule_id,
                        ShiftSchedule.user_id == db_user.id
                    )
                )
                schedule_result = await session.execute(schedule_query)
                schedule = schedule_result.scalar_one_or_none()
                
                if not schedule:
                    return {
                        'success': False,
                        'error': 'Запланированная смена не найдена'
                    }
                
                # Проверяем, можно ли отменить смену
                if not schedule.can_be_cancelled():
                    return {
                        'success': False,
                        'error': 'Смену нельзя отменить менее чем за час до начала'
                    }
                
                # Отменяем смену
                schedule.status = 'cancelled'
                await session.commit()
                
                logger.info(f"Scheduled shift cancelled: id={schedule_id}")
                
                return {
                    'success': True,
                    'message': f'Смена на {schedule.formatted_time_range} отменена'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling scheduled shift: {e}")
            return {
                'success': False,
                'error': f'Ошибка при отмене смены: {str(e)}'
            }
    
    async def get_upcoming_shifts_for_reminder(
        self,
        hours_before: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Получает предстоящие смены для отправки напоминаний.
        
        Args:
            hours_before: За сколько часов до начала отправлять напоминание
            
        Returns:
            Список смен для напоминаний
        """
        try:
            async with get_async_session() as session:
                # Временные рамки для напоминаний
                now = datetime.now(timezone.utc)
                reminder_time = now + timedelta(hours=hours_before)
                
                query = select(ShiftSchedule).options(
                    joinedload(ShiftSchedule.user),
                    joinedload(ShiftSchedule.object)
                ).where(
                    and_(
                        ShiftSchedule.status.in_(['planned', 'confirmed']),
                        ShiftSchedule.notification_sent == False,
                        ShiftSchedule.planned_start <= reminder_time,
                        ShiftSchedule.planned_start > now
                    )
                )
                
                result = await session.execute(query)
                schedules = result.scalars().all()
                
                reminders = []
                for schedule in schedules:
                    reminders.append({
                        'schedule_id': schedule.id,
                        'user_telegram_id': schedule.user.telegram_id,
                        'user_name': schedule.user.full_name,
                        'object_name': schedule.object.name,
                        'formatted_time_range': schedule.formatted_time_range,
                        'planned_start': schedule.planned_start,
                        'time_until_start': schedule.time_until_start
                    })
                
                return reminders
                
        except Exception as e:
            logger.error(f"Error getting upcoming shifts for reminder: {e}")
            return []
    
    async def mark_notification_sent(self, schedule_id: int) -> bool:
        """
        Отмечает, что уведомление о смене отправлено.
        
        Args:
            schedule_id: ID запланированной смены
            
        Returns:
            Успешность операции
        """
        try:
            async with get_async_session() as session:
                query = select(ShiftSchedule).where(ShiftSchedule.id == schedule_id)
                result = await session.execute(query)
                schedule = result.scalar_one_or_none()
                
                if schedule:
                    schedule.notification_sent = True
                    await session.commit()
                    return True
                    
                return False
                
        except Exception as e:
            logger.error(f"Error marking notification sent: {e}")
            return False
