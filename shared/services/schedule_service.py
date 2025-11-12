"""Общий сервис для планирования смен с интеграцией тайм-слотов."""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, time, timezone, date
from core.logging.logger import logger
from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper, convert_utc_to_local
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.time_slot import TimeSlot
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload
from .base_service import BaseService


def _time_to_minutes(time_obj: time) -> int:
    return time_obj.hour * 60 + time_obj.minute if time_obj else 0


def _minutes_to_time_str(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: List[Tuple[int, int]] = []
    current_start, current_end = sorted_intervals[0]
    for start, end in sorted_intervals[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    return merged


def _calculate_free_ranges(slot_start_minutes: int, slot_end_minutes: int, busy_intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if slot_end_minutes <= slot_start_minutes:
        return []
    if not busy_intervals:
        return [(slot_start_minutes, slot_end_minutes)]
    merged = _merge_intervals(busy_intervals)
    free_ranges: List[Tuple[int, int]] = []
    cursor = slot_start_minutes
    for start, end in merged:
        if start > cursor:
            free_ranges.append((cursor, min(start, slot_end_minutes)))
        cursor = max(cursor, end)
        if cursor >= slot_end_minutes:
            break
    if cursor < slot_end_minutes:
        free_ranges.append((cursor, slot_end_minutes))
    return [(start, end) for start, end in free_ranges if end > start]


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
                object_query = select(Object).where(Object.id == object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()

                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }

                object_timezone = obj.timezone or timezone_helper.default_timezone_str

                # Получаем объект
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
                    slot_availability = self._build_slot_availability(slot, shifts, object_timezone)
                    if not slot_availability['has_free_capacity']:
                        continue

                    scheduled_count = slot_availability['scheduled_count']
                    availability = f"{scheduled_count}/{slot.max_employees}"

                    available_slots.append({
                        'id': slot.id,
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot.end_time.strftime('%H:%M'),
                        'hourly_rate': float(slot.hourly_rate) if slot.hourly_rate else None,
                        'description': slot.notes or '',
                        'max_employees': slot.max_employees,
                        'availability': availability,
                        'scheduled_count': scheduled_count,
                        'positions': slot_availability['positions'],
                        'first_free_interval': slot_availability['first_free_interval'],
                        'free_intervals': slot_availability['flattened_free_intervals'],
                        'has_free_capacity': slot_availability['has_free_capacity']
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
    
    def _build_slot_availability(
        self,
        slot: TimeSlot,
        all_shifts: List[ShiftSchedule],
        object_timezone: str
    ) -> Dict[str, Any]:
        slot_start_minutes = _time_to_minutes(slot.start_time)
        slot_end_minutes = _time_to_minutes(slot.end_time)

        if slot_end_minutes <= slot_start_minutes:
            return {
                'positions': [],
                'first_free_interval': None,
                'flattened_free_intervals': [],
                'scheduled_count': 0,
                'has_free_capacity': False
            }

        max_employees = max(1, slot.max_employees or 1)

        relevant_shifts: List[Tuple[int, int]] = []
        scheduled_entities: List[ShiftSchedule] = []

        for shift in all_shifts:
            if shift.object_id != slot.object_id:
                continue

            local_start = convert_utc_to_local(shift.planned_start, object_timezone)
            local_end = convert_utc_to_local(shift.planned_end, object_timezone)

            if not local_start or not local_end:
                continue

            if local_start.date() != slot.slot_date:
                continue

            shift_slot_id = getattr(shift, "time_slot_id", None)
            matches_slot = shift_slot_id == slot.id

            if not matches_slot and shift_slot_id is not None:
                continue

            shift_start_minutes = _time_to_minutes(local_start.time())
            shift_end_minutes = _time_to_minutes(local_end.time())

            overlap_start = max(slot_start_minutes, shift_start_minutes)
            overlap_end = min(slot_end_minutes, shift_end_minutes)

            if overlap_end <= overlap_start:
                continue

            relevant_shifts.append((overlap_start, overlap_end))
            scheduled_entities.append(shift)

        relevant_shifts.sort(key=lambda interval: interval[0])

        positions: List[Dict[str, Any]] = [
            {'index': idx + 1, 'busy': []} for idx in range(max_employees)
        ]

        for interval in relevant_shifts:
            assigned = False
            for position in positions:
                busy_intervals = position['busy']
                if not busy_intervals or busy_intervals[-1][1] <= interval[0]:
                    busy_intervals.append(interval)
                    assigned = True
                    break
            if not assigned:
                # Все позиции заняты в этот момент — добавляем в позицию с самым ранним освобождением
                target_position = min(
                    positions,
                    key=lambda pos: pos['busy'][-1][1] if pos['busy'] else -1
                )
                target_position['busy'].append(interval)

        position_outputs: List[Dict[str, Any]] = []
        flattened_free_intervals: List[Dict[str, Any]] = []
        first_free_interval: Optional[Dict[str, Any]] = None

        for position in positions:
            merged_busy = _merge_intervals(position['busy'])
            free_ranges = _calculate_free_ranges(slot_start_minutes, slot_end_minutes, merged_busy)

            busy_intervals_output = [
                {
                    'start': _minutes_to_time_str(start),
                    'end': _minutes_to_time_str(end),
                    'start_minutes': start,
                    'end_minutes': end
                }
                for start, end in merged_busy
            ]

            free_intervals_output = []
            for start, end in free_ranges:
                interval_info = {
                    'start': _minutes_to_time_str(start),
                    'end': _minutes_to_time_str(end),
                    'start_minutes': start,
                    'end_minutes': end,
                    'duration_minutes': end - start
                }
                free_intervals_output.append({
                    'start': interval_info['start'],
                    'end': interval_info['end'],
                    'duration_minutes': interval_info['duration_minutes']
                })

                flattened_free_intervals.append({
                    'position_index': position['index'],
                    **interval_info
                })

                if first_free_interval is None:
                    first_free_interval = {
                        'position_index': position['index'],
                        'start': interval_info['start'],
                        'end': interval_info['end'],
                        'duration_minutes': interval_info['duration_minutes']
                    }

            position_outputs.append({
                'index': position['index'],
                'busy_intervals': busy_intervals_output,
                'free_intervals': free_intervals_output
            })

        flattened_free_intervals.sort(key=lambda item: item['start_minutes'])

        return {
            'positions': position_outputs,
            'first_free_interval': first_free_interval,
            'flattened_free_intervals': flattened_free_intervals,
            'scheduled_count': len(scheduled_entities),
            'has_free_capacity': first_free_interval is not None
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
                
                # Получаем объект для timezone
                object_query = select(Object).where(Object.id == time_slot.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }

                object_timezone = obj.timezone or timezone_helper.default_timezone_str

                # Проверяем, что время находится в пределах тайм-слота
                if start_time < time_slot.start_time or end_time > time_slot.end_time:
                    return {
                        'success': False,
                        'error': f'Время работы должно быть в пределах тайм-слота: {time_slot.formatted_time_range}'
                    }

                booked_schedules_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.object_id == time_slot.object_id,
                        func.date(ShiftSchedule.planned_start) == time_slot.slot_date,
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                )
                booked_result = await session.execute(booked_schedules_query)
                booked_schedules = booked_result.scalars().all()

                slot_availability = self._build_slot_availability(
                    time_slot,
                    booked_schedules,
                    object_timezone
                )

                if not slot_availability['has_free_capacity']:
                    return {
                        'success': False,
                        'error': 'Тайм-слот полностью занят'
                    }

                requested_start_minutes = _time_to_minutes(start_time)
                requested_end_minutes = _time_to_minutes(end_time)

                matching_interval = next(
                    (
                        interval for interval in slot_availability['flattened_free_intervals']
                        if interval['start_minutes'] <= requested_start_minutes
                        and interval['end_minutes'] >= requested_end_minutes
                    ),
                    None
                )

                if not matching_interval:
                    available_intervals_text = ", ".join(
                        f"{interval['start']}-{interval['end']}"
                        for interval in slot_availability['flattened_free_intervals']
                    ) or 'Нет свободных интервалов'
                    return {
                        'success': False,
                        'error': 'Выбранное время не соответствует доступным интервалам. Доступные интервалы: ' + available_intervals_text
                    }
                
                # Конвертируем локальное время объекта в UTC для корректного хранения
                import pytz
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


