"""Сервис для планирования смен с интеграцией тайм-слотов."""

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


class ScheduleService:
    """Сервис для планирования смен с интеграцией тайм-слотов."""
    
    def __init__(self):
        """Инициализация сервиса."""
        logger.info("ScheduleService initialized")
    
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
                # Получаем все тайм-слоты на дату
                time_slots_query = select(TimeSlot).where(
                    and_(
                        TimeSlot.object_id == object_id,
                        TimeSlot.slot_date == target_date,
                        TimeSlot.is_active == True
                    )
                )
                time_slots_result = await session.execute(time_slots_query)
                time_slots = time_slots_result.scalars().all()
                
                if not time_slots:
                    return {
                        'success': False,
                        'error': 'На эту дату нет доступных тайм-слотов'
                    }
                
                # Получаем забронированные смены на эту дату
                booked_schedules_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.object_id == object_id,
                        func.date(ShiftSchedule.planned_start) == target_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                )
                booked_result = await session.execute(booked_schedules_query)
                booked_schedules = booked_result.scalars().all()
                
                available_slots = []
                
                from datetime import datetime, time as time_type
                
                for slot in time_slots:
                    # Проверяем, не прошло ли время для сегодняшней даты
                    if target_date == date.today():
                        current_time = datetime.now().time()
                        # Если текущее время больше времени окончания слота + 1 минута, пропускаем
                        if current_time > slot.end_time:
                            from datetime import timedelta
                            end_time_plus_minute = (datetime.combine(date.today(), slot.end_time) + timedelta(minutes=1)).time()
                            if current_time > end_time_plus_minute:
                                continue
                    
                    # Получаем доступные интервалы в слоте
                    available_intervals = slot.get_available_intervals(booked_schedules)
                    
                    if available_intervals:
                        # Подсчитываем занятые места в этом тайм-слоте
                        occupied_count = 0
                        for booked_schedule in booked_schedules:
                            # Проверяем, что смена связана с этим тайм-слотом
                            if (booked_schedule.time_slot_id == slot.id):
                                occupied_count += 1
                            # Если time_slot_id не установлен, проверяем по времени (для старых записей)
                            elif (booked_schedule.object_id == slot.object_id and
                                  booked_schedule.planned_start.date() == slot.slot_date and
                                  booked_schedule.time_slot_id is None):
                                # Проверяем пересечение времени
                                if (booked_schedule.planned_start.time() < slot.end_time and
                                    booked_schedule.planned_end.time() > slot.start_time):
                                    occupied_count += 1
                        
                        available_slots.append({
                            "id": slot.id,
                            "start_time": slot.start_time.strftime('%H:%M'),
                            "end_time": slot.end_time.strftime('%H:%M'),
                            "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else None,
                            "max_employees": slot.max_employees,
                            "occupied_employees": occupied_count,
                            "availability": f"{occupied_count}/{slot.max_employees}",
                            "is_additional": slot.is_additional,
                            "notes": slot.notes,
                            "available_intervals": [
                                {
                                    "start": interval[0].strftime('%H:%M'),
                                    "end": interval[1].strftime('%H:%M'),
                                    "duration_hours": round(
                                        (interval[1].hour * 3600 + interval[1].minute * 60 - 
                                         interval[0].hour * 3600 - interval[0].minute * 60) / 3600, 2
                                    )
                                }
                                for interval in available_intervals
                            ],
                            "total_duration": slot.duration_hours
                        })
                
                return {
                    'success': True,
                    'available_slots': available_slots,
                    'date': target_date.strftime('%d.%m.%Y')
                }
                
        except Exception as e:
            logger.error(f"Error getting available time slots: {e}")
            return {
                'success': False,
                'error': f'Ошибка получения тайм-слотов: {str(e)}'
            }
    
    async def create_scheduled_shift_from_timeslot(
        self,
        user_id: int,  # telegram_id
        time_slot_id: int,
        start_time: time,
        end_time: time,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает запланированную смену на основе тайм-слота.
        
        Args:
            user_id: telegram_id пользователя
            time_slot_id: ID тайм-слота
            start_time: Время начала работы
            end_time: Время окончания работы
            notes: Заметки к смене
            
        Returns:
            Результат создания запланированной смены
        """
        try:
            logger.info(
                f"Creating scheduled shift from timeslot: user_id={user_id}, "
                f"timeslot_id={time_slot_id}, time={start_time}-{end_time}"
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
                
                # Получаем тайм-слот
                timeslot_query = select(TimeSlot).where(TimeSlot.id == time_slot_id)
                timeslot_result = await session.execute(timeslot_query)
                timeslot = timeslot_result.scalar_one_or_none()
                
                if not timeslot:
                    return {
                        'success': False,
                        'error': 'Тайм-слот не найден'
                    }
                
                # Проверяем, что время находится в пределах тайм-слота
                if start_time < timeslot.start_time or end_time > timeslot.end_time:
                    return {
                        'success': False,
                        'error': f'Время работы должно быть в пределах тайм-слота: {timeslot.formatted_time_range}'
                    }
                
                # Проверяем, что выбранное время соответствует доступному интервалу
                # Получаем забронированные смены для проверки доступных интервалов
                booked_schedules_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.object_id == timeslot.object_id,
                        func.date(ShiftSchedule.planned_start) == timeslot.slot_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                )
                booked_result = await session.execute(booked_schedules_query)
                booked_schedules = booked_result.scalars().all()
                
                # Получаем доступные интервалы в тайм-слоте
                available_intervals = timeslot.get_available_intervals(booked_schedules)
                
                # Проверяем, что выбранное время соответствует одному из доступных интервалов
                time_fits_interval = False
                for interval in available_intervals:
                    interval_start, interval_end = interval
                    if start_time >= interval_start and end_time <= interval_end:
                        time_fits_interval = True
                        break
                
                if not time_fits_interval:
                    return {
                        'success': False,
                        'error': 'Выбранное время не соответствует доступным интервалам в тайм-слоте. Доступные интервалы: ' + ", ".join([f"{interval[0].strftime('%H:%M')}-{interval[1].strftime('%H:%M')}" for interval in available_intervals])
                    }
                
                # Проверяем доступность времени
                availability_check = await self._check_time_availability_in_timeslot(
                    session, db_user.id, timeslot, start_time, end_time
                )
                
                if not availability_check['available']:
                    return {
                        'success': False,
                        'error': availability_check['error']
                    }
                
                # Создаем запланированную смену
                scheduled_shift = ShiftSchedule(
                    user_id=db_user.id,
                    object_id=timeslot.object_id,
                    time_slot_id=time_slot_id,
                    planned_start=datetime.combine(timeslot.slot_date, start_time),
                    planned_end=datetime.combine(timeslot.slot_date, end_time),
                    hourly_rate=timeslot.hourly_rate,
                    notes=notes
                )
                
                session.add(scheduled_shift)
                await session.commit()
                
                logger.info(
                    f"Successfully created scheduled shift from timeslot: "
                    f"user_id={db_user.id}, timeslot_id={time_slot_id}"
                )
                
                return {
                    'success': True,
                    'scheduled_shift_id': scheduled_shift.id,
                    'message': f'Смена запланирована на {timeslot.slot_date.strftime("%d.%m.%Y")} с {start_time.strftime("%H:%M")} до {end_time.strftime("%H:%M")}'
                }
                
        except Exception as e:
            logger.error(f"Error creating scheduled shift from timeslot: {e}")
            return {
                'success': False,
                'error': f'Ошибка планирования смены: {str(e)}'
            }
    
    async def _check_time_availability_in_timeslot(
        self, 
        session, 
        user_id: int, 
        timeslot: TimeSlot, 
        start_time: time, 
        end_time: time
    ) -> Dict[str, Any]:
        """
        Проверяет доступность времени в тайм-слоте.
        
        Args:
            session: Сессия БД
            user_id: ID пользователя в БД
            timeslot: Тайм-слот
            start_time: Время начала
            end_time: Время окончания
            
        Returns:
            Словарь с результатом проверки
        """
        try:
            # Проверяем, есть ли уже запланированные смены у пользователя в это время
            existing_shifts_query = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.user_id == user_id,
                    ShiftSchedule.status.in_(["planned", "confirmed"]),
                    or_(
                        and_(
                            ShiftSchedule.planned_start < datetime.combine(timeslot.slot_date, end_time),
                            ShiftSchedule.planned_end > datetime.combine(timeslot.slot_date, start_time)
                        )
                    )
                )
            )
            
            existing_result = await session.execute(existing_shifts_query)
            existing_shifts = existing_result.scalars().all()
            
            if existing_shifts:
                conflicts = []
                for shift in existing_shifts:
                    conflicts.append({
                        'object_name': shift.object.name if shift.object else 'Неизвестный объект',
                        'start_time': shift.planned_start.strftime('%d.%m.%Y %H:%M'),
                        'end_time': shift.planned_end.strftime('%H:%M')
                    })
                
                return {
                    'available': False,
                    'error': 'У вас уже есть запланированные смены в это время',
                    'conflicts': conflicts
                }
            
            # Проверяем, не превышает ли количество сотрудников лимит тайм-слота
            if timeslot.max_employees > 1:
                # Получаем количество уже забронированных смен в этом тайм-слоте
                booked_count_query = select(func.count(ShiftSchedule.id)).where(
                    and_(
                        ShiftSchedule.object_id == timeslot.object_id,
                        func.date(ShiftSchedule.planned_start) == timeslot.slot_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"]),
                        or_(
                            and_(
                                ShiftSchedule.planned_start < datetime.combine(timeslot.slot_date, end_time),
                                ShiftSchedule.planned_end > datetime.combine(timeslot.slot_date, start_time)
                            )
                        )
                    )
                )
                
                booked_count_result = await session.execute(booked_count_query)
                booked_count = booked_count_result.scalar()
                
                if booked_count >= timeslot.max_employees:
                    return {
                        'available': False,
                        'error': f'Тайм-слот уже полностью занят (максимум {timeslot.max_employees} сотрудников)'
                    }
            
            return {'available': True}
            
        except Exception as e:
            logger.error(f"Error checking time availability in timeslot: {e}")
            return {
                'available': False,
                'error': f'Ошибка проверки доступности: {str(e)}'
            }
    
    async def create_scheduled_shift(
        self,
        user_id: int,  # telegram_id
        object_id: int,
        planned_start: datetime,
        planned_end: datetime,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает запланированную смену (устаревший метод, используйте create_scheduled_shift_from_timeslot).
        
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
                f"Creating scheduled shift (legacy method): user_id={user_id}, object_id={object_id}, "
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
                    notes=notes
                )
                
                session.add(scheduled_shift)
                await session.commit()
                
                logger.info(
                    f"Successfully created scheduled shift: user_id={db_user.id}, object_id={object_id}"
                )
                
                return {
                    'success': True,
                    'scheduled_shift_id': scheduled_shift.id,
                    'message': 'Смена успешно запланирована'
                }
                
        except Exception as e:
            logger.error(f"Error creating scheduled shift: {e}")
            return {
                'success': False,
                'error': f'Ошибка планирования смены: {str(e)}'
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
