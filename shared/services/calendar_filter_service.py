"""Универсальный сервис фильтрации данных календаря."""

import logging
import hashlib
import json
import math
from collections import defaultdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date, time, timedelta
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift

from shared.models.calendar_data import (
    CalendarTimeslot,
    CalendarShift,
    CalendarData,
    CalendarFilter,
    ShiftType,
    ShiftStatus,
    TimeslotStatus
)
from shared.services.object_access_service import ObjectAccessService
from core.cache.redis_cache import cached
from core.cache.cache_service import CacheService

logger = logging.getLogger(__name__)

def convert_datetime_to_local(dt, object_timezone: str = 'Europe/Moscow') -> str:
    """Конвертировать datetime в локальную временную зону объекта."""
    if not dt:
        return ''
    
    try:
        # Проверяем, что dt - это datetime объект
        if isinstance(dt, str):
            logger.warning(f"Received string instead of datetime: {dt}")
            return dt  # Возвращаем строку как есть
        
        # Импортируем внутри функции, чтобы избежать циклических импортов
        from apps.web.utils.timezone_utils import WebTimezoneHelper
        web_timezone_helper = WebTimezoneHelper()
        
        # Конвертируем в локальную временную зону
        result = web_timezone_helper.format_datetime_with_timezone(dt, object_timezone, '%Y-%m-%dT%H:%M:%S')
        logger.debug(f"Converted {dt} to {result} (timezone: {object_timezone})")
        return result
        
    except Exception as e:
        logger.error(f"Error converting datetime to local timezone: {e}, dt type: {type(dt)}, dt value: {dt}")
        # Fallback: возвращаем время как есть
        if hasattr(dt, 'strftime'):
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            return str(dt) if dt else ''


class CalendarFilterService:
    """Универсальный сервис для получения данных календаря для всех ролей."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.object_access_service = ObjectAccessService(db)
        # Простой кэш в памяти (в продакшене лучше использовать Redis)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
    
    def _generate_cache_key(self, user_telegram_id: int, user_role: str, 
                           date_range_start: date, date_range_end: date, 
                           object_filter: Optional[List[int]] = None) -> str:
        """Генерирует ключ кэша для запроса."""
        cache_data = {
            'user_telegram_id': user_telegram_id,
            'user_role': user_role,
            'date_range_start': date_range_start.isoformat(),
            'date_range_end': date_range_end.isoformat(),
            'object_filter': sorted(object_filter) if object_filter else None
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Получает данные из кэша."""
        if cache_key in self._cache and cache_key in self._cache_ttl:
            if datetime.now() < self._cache_ttl[cache_key]:
                return self._cache[cache_key]
            else:
                # Удаляем устаревшие данные
                del self._cache[cache_key]
                del self._cache_ttl[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl_minutes: int = 5):
        """Сохраняет данные в кэш."""
        self._cache[cache_key] = data
        self._cache_ttl[cache_key] = datetime.now() + timedelta(minutes=ttl_minutes)
    
    async def get_calendar_data(
        self,
        user_telegram_id: int,
        user_role: str,
        date_range_start: date,
        date_range_end: date,
        object_filter: Optional[List[int]] = None
    ) -> CalendarData:
        """
        Получить унифицированные данные календаря для пользователя.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_role: Роль пользователя (owner, manager, employee, applicant)
            date_range_start: Начало периода
            date_range_end: Конец периода
            object_filter: Фильтр по объектам (None = все доступные)
            
        Returns:
            CalendarData с тайм-слотами и сменами
        """
        try:
            # Временно отключаем кэш для отладки
            # cache_key = self._generate_cache_key(
            #     user_telegram_id, user_role, date_range_start, date_range_end, object_filter
            # )
            # cached_data = self._get_from_cache(cache_key)
            # if cached_data:
            #     logger.debug(f"Cache hit for user {user_telegram_id}")
            #     return cached_data
            
            logger.info(f"Getting calendar data for user {user_telegram_id}, role {user_role}, period {date_range_start} to {date_range_end}")
            
            # Получаем доступные объекты
            accessible_objects = await self.object_access_service.get_accessible_objects(
                user_telegram_id, user_role
            )
            
            logger.info(f"CalendarFilterService: Found {len(accessible_objects)} accessible objects for user {user_telegram_id}, role {user_role}")
            for obj in accessible_objects:
                logger.info(f"  - Object: {obj['name']} (ID: {obj['id']})")
            
            if not accessible_objects:
                logger.warning(f"No accessible objects for user {user_telegram_id}")
                return CalendarData(
                    timeslots=[],
                    shifts=[],
                    date_range_start=date_range_start,
                    date_range_end=date_range_end,
                    user_role=user_role,
                    accessible_objects=[]
                )
            
            # Определяем объекты для запроса
            if object_filter:
                # Фильтруем только по доступным объектам
                accessible_object_ids = [obj['id'] for obj in accessible_objects]
                filtered_object_ids = [obj_id for obj_id in object_filter if obj_id in accessible_object_ids]
            else:
                filtered_object_ids = [obj['id'] for obj in accessible_objects]
            
            if not filtered_object_ids:
                logger.warning(f"No valid objects in filter for user {user_telegram_id}")
                return CalendarData(
                    timeslots=[],
                    shifts=[],
                    date_range_start=date_range_start,
                    date_range_end=date_range_end,
                    user_role=user_role,
                    accessible_objects=accessible_objects
                )
            
            # Получаем тайм-слоты и смены параллельно
            timeslots = await self._get_timeslots(filtered_object_ids, date_range_start, date_range_end, accessible_objects)
            shifts = await self._get_shifts(filtered_object_ids, date_range_start, date_range_end, accessible_objects)
            
            # Обновляем статусы тайм-слотов на основе смен
            timeslots = self._update_timeslot_statuses(timeslots, shifts, accessible_objects)
            
            logger.info(f"Found {len(timeslots)} timeslots and {len(shifts)} shifts for user {user_telegram_id}")
            
            # Создаем результат
            result = CalendarData(
                timeslots=timeslots,
                shifts=shifts,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                user_role=user_role,
                accessible_objects=accessible_objects
            )
            
            # Временно отключаем сохранение в кэш для отладки
            # self._set_cache(cache_key, result, ttl_minutes=5)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting calendar data for user {user_telegram_id}: {e}", exc_info=True)
            return CalendarData(
                timeslots=[],
                shifts=[],
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                user_role=user_role,
                accessible_objects=[]
            )
    
    @cached(ttl=timedelta(minutes=10), key_prefix="calendar_timeslots")
    async def _get_timeslots(
        self,
        object_ids: List[int],
        date_range_start: date,
        date_range_end: date,
        accessible_objects: List[Dict[str, Any]]
    ) -> List[CalendarTimeslot]:
        """Получить тайм-слоты для объектов."""
        try:
            logger.info(f"_get_timeslots called with object_ids={object_ids}, date_range={date_range_start} to {date_range_end}")
            # Создаем словарь объектов для быстрого доступа
            objects_map = {obj['id']: obj for obj in accessible_objects}
            
            # Оптимизированный запрос с индексами
            timeslots_query = select(TimeSlot).options(
                selectinload(TimeSlot.object)
            ).where(
                and_(
                    TimeSlot.object_id.in_(object_ids),
                    TimeSlot.slot_date >= date_range_start,
                    TimeSlot.slot_date <= date_range_end,  # Включаем конечную дату
                    TimeSlot.is_active == True
                )
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
            
            timeslots_result = await self.db.execute(timeslots_query)
            timeslots = timeslots_result.scalars().all()
            
            logger.info(f"CalendarFilterService: Found {len(timeslots)} timeslots in database for objects {object_ids}")
            for slot in timeslots:
                logger.info(f"  - Timeslot {slot.id}: {slot.slot_date} {slot.start_time}-{slot.end_time} (object {slot.object_id})")
            
            calendar_timeslots = []
            for slot in timeslots:
                obj_info = objects_map.get(slot.object_id)
                if not obj_info:
                    logger.warning(f"Timeslot {slot.id} references object {slot.object_id} not in accessible objects")
                    continue
                
                calendar_timeslots.append(CalendarTimeslot(
                    id=slot.id,
                    object_id=slot.object_id,
                    object_name=obj_info['name'],
                    date=slot.slot_date,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    hourly_rate=float(slot.hourly_rate) if slot.hourly_rate else obj_info['hourly_rate'],
                    max_employees=slot.max_employees if slot.max_employees is not None else 1,
                    is_active=slot.is_active,
                    notes=slot.notes,
                    work_conditions=obj_info.get('work_conditions'),
                    shift_tasks=obj_info.get('shift_tasks'),
                    coordinates=obj_info.get('coordinates'),
                    can_edit=obj_info.get('can_edit', False),
                    can_plan=obj_info.get('can_edit_schedule', False),
                    can_view=obj_info.get('can_view', True)
                ))
            
            logger.info(f"Found {len(calendar_timeslots)} timeslots")
            return calendar_timeslots
            
        except Exception as e:
            logger.error(f"Error getting timeslots: {e}", exc_info=True)
            return []
    
    async def _get_object_timezones(self, object_ids: List[int]) -> Dict[int, str]:
        """Получить временные зоны объектов."""
        try:
            from domain.entities.object import Object
            query = select(Object.id, Object.timezone).where(Object.id.in_(object_ids))
            result = await self.db.execute(query)
            timezones = {}
            for row in result:
                timezones[row.id] = row.timezone or 'Europe/Moscow'
            return timezones
        except Exception as e:
            logger.error(f"Error getting object timezones: {e}", exc_info=True)
            return {obj_id: 'Europe/Moscow' for obj_id in object_ids}
    
    @cached(ttl=timedelta(minutes=3), key_prefix="calendar_shifts")
    async def _get_shifts(
        self,
        object_ids: List[int],
        date_range_start: date,
        date_range_end: date,
        accessible_objects: List[Dict[str, Any]]
    ) -> List[CalendarShift]:
        """Получить смены для объектов с правильной фильтрацией."""
        try:
            # Создаем словарь объектов для быстрого доступа
            objects_map = {obj['id']: obj for obj in accessible_objects}
            
            # Получаем временные зоны объектов
            object_timezones = await self._get_object_timezones(object_ids)
            
            calendar_shifts = []
            
            # 1. Получаем фактические смены (активные и завершенные)
            actual_shifts = await self._get_actual_shifts(object_ids, date_range_start, date_range_end, objects_map, object_timezones)
            calendar_shifts.extend(actual_shifts)
            
            # 2. Получаем запланированные смены (только те, которые НЕ начались)
            # Исключаем те, для которых уже есть фактические смены
            actual_shift_ids = {shift.schedule_id for shift in actual_shifts if shift.schedule_id}
            planned_shifts = await self._get_planned_shifts(object_ids, date_range_start, date_range_end, objects_map, object_timezones, exclude_schedule_ids=actual_shift_ids)
            calendar_shifts.extend(planned_shifts)
            
            logger.info(f"Found {len(planned_shifts)} planned shifts and {len(actual_shifts)} actual shifts")
            return calendar_shifts
            
        except Exception as e:
            logger.error(f"Error getting shifts: {e}", exc_info=True)
            return []
    
    async def _get_planned_shifts(
        self,
        object_ids: List[int],
        date_range_start: date,
        date_range_end: date,
        objects_map: Dict[int, Dict[str, Any]],
        object_timezones: Dict[int, str],
        exclude_schedule_ids: Optional[set] = None
    ) -> List[CalendarShift]:
        """Получить запланированные смены, исключая те, которые уже начались."""
        try:
            # КРИТИЧЕСКИ ВАЖНО: Исключаем запланированные смены, которые уже начались
            # Используем LEFT JOIN для проверки отсутствия фактических смен
            conditions = [
                ShiftSchedule.object_id.in_(object_ids),
                ShiftSchedule.planned_start >= datetime.combine(date_range_start, time.min),
                ShiftSchedule.planned_start < datetime.combine(date_range_end, time.max),
                ShiftSchedule.status.in_(["planned", "confirmed"]),
                # ИСКЛЮЧАЕМ смены, которые уже начались
                ShiftSchedule.actual_shift_id.is_(None),
                # ИСКЛЮЧАЕМ отменённые смены
                ShiftSchedule.status != "cancelled"
            ]
            
            # Исключаем запланированные смены, для которых уже есть фактические
            if exclude_schedule_ids:
                conditions.append(ShiftSchedule.id.notin_(exclude_schedule_ids))
            
            planned_query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.user),
                selectinload(ShiftSchedule.object)
            ).where(and_(*conditions)).order_by(ShiftSchedule.planned_start)
            
            planned_result = await self.db.execute(planned_query)
            planned_shifts = planned_result.scalars().all()
            
            # Дополнительная проверка: исключаем смены, для которых есть связанные Shift с is_planned=True
            filtered_planned_shifts = []
            for shift_schedule in planned_shifts:
                # Проверяем, есть ли связанная фактическая смена
                actual_shift_query = select(Shift).where(
                    and_(
                        Shift.schedule_id == shift_schedule.id,
                        Shift.is_planned == True
                    )
                )
                actual_shift_result = await self.db.execute(actual_shift_query)
                actual_shift = actual_shift_result.scalar_one_or_none()
                
                if not actual_shift:  # Нет связанной фактической смены - показываем
                    obj_info = objects_map.get(shift_schedule.object_id)
                    if obj_info and shift_schedule.user:
                        object_timezone = object_timezones.get(shift_schedule.object_id, 'Europe/Moscow')
                        filtered_planned_shifts.append(CalendarShift(
                            id=f"schedule_{shift_schedule.id}",  # Добавляем префикс для запланированных смен
                            user_id=shift_schedule.user_id,
                            user_name=f"{shift_schedule.user.first_name or ''} {shift_schedule.user.last_name or ''}".strip(),
                            object_id=shift_schedule.object_id,
                            object_name=obj_info['name'],
                            start_time=shift_schedule.planned_start,  # Отключаем конвертацию - делается в API
                            time_slot_id=shift_schedule.time_slot_id,
                            planned_start=shift_schedule.planned_start,
                            planned_end=shift_schedule.planned_end,
                            shift_type=ShiftType.PLANNED,
                            status=ShiftStatus(shift_schedule.status),
                            hourly_rate=float(shift_schedule.hourly_rate) if shift_schedule.hourly_rate else None,
                            notes=shift_schedule.notes,
                            is_planned=True,
                            schedule_id=shift_schedule.id,
                            can_edit=obj_info.get('can_edit', False),
                            can_cancel=obj_info.get('can_edit_schedule', False),
                            can_view=obj_info.get('can_view', True),
                            timezone=obj_info.get('timezone', 'Europe/Moscow')
                        ))
            
            logger.info(f"Found {len(filtered_planned_shifts)} planned shifts (after filtering)")
            return filtered_planned_shifts
            
        except Exception as e:
            logger.error(f"Error getting planned shifts: {e}", exc_info=True)
            return []
    
    async def _get_actual_shifts(
        self,
        object_ids: List[int],
        date_range_start: date,
        date_range_end: date,
        objects_map: Dict[int, Dict[str, Any]],
        object_timezones: Dict[int, str]
    ) -> List[CalendarShift]:
        """Получить фактические смены (активные и завершенные)."""
        try:
            actual_query = select(Shift).options(
                selectinload(Shift.user),
                selectinload(Shift.object)
            ).where(
                and_(
                    Shift.object_id.in_(object_ids),
                    Shift.start_time >= datetime.combine(date_range_start, time.min),
                    Shift.start_time < datetime.combine(date_range_end, time.max),
                    # ИСКЛЮЧАЕМ отменённые смены
                    Shift.status.in_(["active", "completed"])
                )
            ).order_by(Shift.start_time)
            
            actual_result = await self.db.execute(actual_query)
            actual_shifts = actual_result.scalars().all()
            
            calendar_shifts = []
            for shift in actual_shifts:
                obj_info = objects_map.get(shift.object_id)
                if obj_info and shift.user:
                    # Определяем тип смены
                    if shift.status == "active":
                        shift_type = ShiftType.ACTIVE
                    elif shift.status == "completed":
                        shift_type = ShiftType.COMPLETED
                    else:
                        shift_type = ShiftType.ACTIVE  # По умолчанию
                    
                    object_timezone = object_timezones.get(shift.object_id, 'Europe/Moscow')
                    calendar_shifts.append(CalendarShift(
                        id=shift.id,
                        user_id=shift.user_id,
                        user_name=f"{shift.user.first_name or ''} {shift.user.last_name or ''}".strip(),
                        object_id=shift.object_id,
                        object_name=obj_info['name'],
                        time_slot_id=shift.time_slot_id,
                        start_time=shift.start_time,  # Отключаем конвертацию - делается в API
                        end_time=shift.end_time,  # Отключаем конвертацию - делается в API
                        shift_type=shift_type,
                        status=ShiftStatus(shift.status),
                        hourly_rate=float(shift.hourly_rate) if shift.hourly_rate else None,
                        total_hours=float(shift.total_hours) if shift.total_hours else None,
                        total_payment=float(shift.total_payment) if shift.total_payment else None,
                        notes=shift.notes,
                        is_planned=shift.is_planned,
                        schedule_id=shift.schedule_id,
                        actual_shift_id=shift.id,
                        start_coordinates=shift.start_coordinates,
                        end_coordinates=shift.end_coordinates,
                        can_edit=obj_info.get('can_edit', False),
                        can_cancel=obj_info.get('can_edit_schedule', False),
                        can_view=obj_info.get('can_view', True),
                        timezone=obj_info.get('timezone', 'Europe/Moscow')
                    ))
            
            logger.info(f"Found {len(calendar_shifts)} actual shifts")
            return calendar_shifts
            
        except Exception as e:
            logger.error(f"Error getting actual shifts: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _format_minutes(value: float) -> str:
        """Форматирует минуты в строку вида '8 ч 24 м'."""
        minutes = max(0, int(round(value)))
        hours, minutes = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(f"{hours} ч")
        if minutes or not parts:
            parts.append(f"{minutes} м")
        return " ".join(parts)

    def _update_timeslot_statuses(
        self,
        timeslots: List[CalendarTimeslot],
        shifts: List[CalendarShift],
        accessible_objects: List[Dict[str, Any]]
    ) -> List[CalendarTimeslot]:
        """Обновить статусы тайм-слотов на основе смен."""
        try:
            shifts_by_timeslot: Dict[int, List[CalendarShift]] = defaultdict(list)
            for shift in shifts:
                if shift.time_slot_id:
                    shifts_by_timeslot[shift.time_slot_id].append(shift)

            objects_map = {obj['id']: obj for obj in accessible_objects}
            timezone_cache: Dict[int, pytz.timezone] = {}

            def get_object_timezone(object_id: int) -> pytz.timezone:
                if object_id in timezone_cache:
                    return timezone_cache[object_id]
                timezone_name = objects_map.get(object_id, {}).get('timezone', 'Europe/Moscow')
                try:
                    tz = pytz.timezone(timezone_name)
                except pytz.UnknownTimeZoneError:
                    tz = pytz.timezone('Europe/Moscow')
                timezone_cache[object_id] = tz
                return tz

            # Шифты без привязки к тайм-слоту (fallback)
            fallback_shifts_by_object: Dict[int, List[CalendarShift]] = defaultdict(list)
            for shift in shifts:
                if not shift.time_slot_id and shift.object_id:
                    fallback_shifts_by_object[shift.object_id].append(shift)

            now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)

            allowed_shift_statuses = {
                ShiftStatus.PLANNED,
                ShiftStatus.CONFIRMED
            }

            for timeslot in timeslots:
                tz = get_object_timezone(timeslot.object_id)

                slot_start_local = tz.localize(datetime.combine(timeslot.date, timeslot.start_time))
                slot_end_local = tz.localize(datetime.combine(timeslot.date, timeslot.end_time))
                slot_duration_minutes = max(0, (slot_end_local - slot_start_local).total_seconds() / 60)
                max_employees = timeslot.max_employees if timeslot.max_employees else 1
                capacity_minutes = slot_duration_minutes * max_employees
                now_local = now_utc.astimezone(tz)

                # Для тайм-слотов, которые уже начались, помечаем как HIDDEN, но НЕ пропускаем
                # чтобы они все равно попали в результат для обработки
                if slot_start_local <= now_local:
                    timeslot.status = TimeslotStatus.HIDDEN
                    timeslot.status_label = ""
                    # Не пропускаем, продолжаем обработку, чтобы тайм-слот попал в результат

                direct_shifts = shifts_by_timeslot.get(timeslot.id, [])
                fallback_candidates = fallback_shifts_by_object.get(timeslot.object_id, [])

                overlap_intervals: List[tuple[datetime, datetime]] = []
                concurrency_events: List[tuple[datetime, int]] = []
                shift_details = []
                actual_intervals = []

                def register_interval(
                    shift: CalendarShift,
                    start_dt: Optional[datetime],
                    end_dt: Optional[datetime],
                    include_in_details: bool
                ) -> None:
                    if not start_dt:
                        return
                    if start_dt.tzinfo is None:
                        start_dt_aware = pytz.UTC.localize(start_dt)
                    else:
                        start_dt_aware = start_dt

                    if end_dt:
                        end_dt_aware = end_dt if end_dt.tzinfo else pytz.UTC.localize(end_dt)
                    else:
                        end_dt_aware = slot_end_local.astimezone(pytz.UTC)

                    start_local = start_dt_aware.astimezone(tz)
                    end_local = end_dt_aware.astimezone(tz)
                    overlap_start = max(start_local, slot_start_local)
                    overlap_end = min(end_local, slot_end_local)
                    if overlap_end <= overlap_start:
                        return

                    overlap_intervals.append((overlap_start, overlap_end))
                    concurrency_events.append((overlap_start, 1))
                    concurrency_events.append((overlap_end, -1))

                    if include_in_details:
                        shift_details.append({
                            "shift": shift,
                            "start_local": overlap_start,
                            "end_local": overlap_end
                        })
                        if shift.shift_type in (ShiftType.ACTIVE, ShiftType.COMPLETED):
                            actual_intervals.append((overlap_start, overlap_end))

                for shift in direct_shifts:
                    if shift.status not in allowed_shift_statuses:
                        continue
                    if shift.shift_type == ShiftType.PLANNED:
                        start_dt = shift.planned_start or shift.start_time
                        end_dt = shift.planned_end or shift.end_time
                    else:
                        start_dt = shift.start_time or shift.planned_start
                        end_dt = shift.end_time or shift.planned_end
                    register_interval(shift, start_dt, end_dt, include_in_details=True)

                for shift in fallback_candidates:
                    if shift.status not in allowed_shift_statuses:
                        continue
                    if shift.shift_type == ShiftType.PLANNED:
                        start_dt = shift.planned_start or shift.start_time
                        end_dt = shift.planned_end or shift.end_time
                    else:
                        start_dt = shift.start_time or shift.planned_start
                        end_dt = shift.end_time or shift.planned_end

                    if not start_dt:
                        continue
                    start_aware = start_dt if start_dt.tzinfo else pytz.UTC.localize(start_dt)
                    if start_aware.astimezone(tz).date() != timeslot.date:
                        continue

                    register_interval(shift, start_dt, end_dt, include_in_details=False)

                occupied_minutes = 0.0
                for interval_start, interval_end in overlap_intervals:
                    occupied_minutes += max(0, (interval_end - interval_start).total_seconds() / 60)

                if capacity_minutes > 0:
                    occupied_minutes = min(capacity_minutes, occupied_minutes)
                    free_minutes = max(0, capacity_minutes - occupied_minutes)
                    occupancy_ratio = occupied_minutes / capacity_minutes
                else:
                    free_minutes = 0.0
                    occupancy_ratio = 0.0

                occupancy_ratio = round(occupancy_ratio, 4)
                timeslot.occupied_minutes = round(occupied_minutes, 2)
                timeslot.free_minutes = round(free_minutes, 2)
                timeslot.occupancy_ratio = occupancy_ratio

                concurrency_events.sort(key=lambda item: (item[0], -item[1]))
                current_concurrency = 0
                max_concurrency = 0
                for _, delta in concurrency_events:
                    current_concurrency += delta
                    max_concurrency = max(max_concurrency, current_concurrency)

                max_concurrency = min(max_employees, max_concurrency)
                timeslot.current_employees = max_concurrency
                timeslot.available_slots = max(0, max_employees - max_concurrency)

                slot_in_past = slot_end_local <= now_local
                slot_in_future = slot_start_local > now_local

                if capacity_minutes > 0 and free_minutes <= 29:
                    timeslot.status = TimeslotStatus.FULLY_FILLED
                    timeslot.status_label = "Заполнено"
                elif occupied_minutes > 0:
                    timeslot.status = TimeslotStatus.PARTIALLY_FILLED
                    timeslot.status_label = "Свободно"
                else:
                    timeslot.status = TimeslotStatus.AVAILABLE
                    timeslot.status_label = "Свободно"

                # Помечаем как HIDDEN только тайм-слоты в прошлом, которые не полностью заполнены
                # Для будущих дней показываем все тайм-слоты, включая свободные
                if slot_in_past and occupancy_ratio < 0.999 and not slot_in_future:
                    timeslot.status = TimeslotStatus.HIDDEN

                formatted_free = self._format_minutes(timeslot.free_minutes) if timeslot.free_minutes > 0 else "0 м"

                delay_label = None
                if slot_in_past and timeslot.free_minutes > 0:
                    delay_label = f"Опоздание {formatted_free}"

                for detail in shift_details:
                    shift = detail["shift"]
                    if shift.shift_type != ShiftType.PLANNED:
                        continue

                    start_local = detail["start_local"]
                    end_local = detail["end_local"]
                    overlaps_actual = any(
                        actual_start < end_local and start_local < actual_end
                        for actual_start, actual_end in actual_intervals
                    )

                    has_past_planned_without_actual = end_local < now_local and not overlaps_actual
                    if has_past_planned_without_actual:
                        shift.status_label = "Не состоялась"

                if delay_label:
                    for detail in shift_details:
                        shift = detail["shift"]
                        if shift.shift_type in (ShiftType.ACTIVE, ShiftType.COMPLETED):
                            shift.status_label = delay_label

                # Проверка полного покрытия тайм-слота запланированными сменами
                # Если есть запланированная смена, которая покрывает весь тайм-слот (от start_time до end_time)
                fully_covered_by_planned = False
                for detail in shift_details:
                    shift = detail["shift"]
                    if shift.shift_type == ShiftType.PLANNED:
                        start_local = detail["start_local"]
                        end_local = detail["end_local"]
                        # Проверяем, покрывает ли смена весь тайм-слот
                        if start_local <= slot_start_local and end_local >= slot_end_local:
                            fully_covered_by_planned = True
                            break
                
                timeslot.fully_occupied = fully_covered_by_planned
                
                # Проверка треков для активных смен
                # Если есть активная смена, открытая по запланированной, проверяем треки
                # Треки определяются на фронте, но здесь можем проверить базовую логику
                # Если все треки заняты (current_employees >= max_employees и нет free_minutes), то has_free_track = False
                has_free_track = True
                if timeslot.current_employees >= timeslot.max_employees and timeslot.free_minutes <= 0:
                    # Проверяем, есть ли активные смены, открытые по запланированным
                    has_active_from_planned = any(
                        shift.shift_type == ShiftType.ACTIVE and shift.schedule_id is not None
                        for shift in direct_shifts
                    )
                    if has_active_from_planned:
                        # Если все треки заняты активными сменами по плану, то нет свободных треков
                        has_free_track = False
                
                timeslot.has_free_track = has_free_track

            return timeslots
            
        except Exception as e:
            logger.error(f"Error updating timeslot statuses: {e}", exc_info=True)
            return timeslots
    
    async def get_calendar_stats(
        self,
        user_telegram_id: int,
        user_role: str,
        date_range_start: date,
        date_range_end: date
    ) -> Dict[str, Any]:
        """Получить статистику календаря."""
        try:
            calendar_data = await self.get_calendar_data(
                user_telegram_id, user_role, date_range_start, date_range_end
            )
            
            # Подсчитываем статистику
            total_hours = sum(shift.duration_hours or 0 for shift in calendar_data.shifts)
            total_payment = sum(shift.total_payment or 0 for shift in calendar_data.shifts)
            
            # Средняя ставка
            hourly_rates = [shift.hourly_rate for shift in calendar_data.shifts if shift.hourly_rate]
            average_hourly_rate = sum(hourly_rates) / len(hourly_rates) if hourly_rates else 0
            
            # Объекты с активностью
            objects_with_shifts = len(set(shift.object_id for shift in calendar_data.shifts))
            objects_with_timeslots = len(set(timeslot.object_id for timeslot in calendar_data.timeslots))
            
            return {
                'total_timeslots': calendar_data.total_timeslots,
                'total_shifts': calendar_data.total_shifts,
                'total_objects': len(calendar_data.accessible_objects),
                'planned_shifts': calendar_data.planned_shifts,
                'active_shifts': calendar_data.active_shifts,
                'completed_shifts': calendar_data.completed_shifts,
                'cancelled_shifts': len([s for s in calendar_data.shifts if s.status == ShiftStatus.CANCELLED]),
                'available_timeslots': len([t for t in calendar_data.timeslots if t.status == TimeslotStatus.AVAILABLE]),
                'partially_filled_timeslots': len([t for t in calendar_data.timeslots if t.status == TimeslotStatus.PARTIALLY_FILLED]),
                'fully_filled_timeslots': len([t for t in calendar_data.timeslots if t.status == TimeslotStatus.FULLY_FILLED]),
                'total_hours': total_hours,
                'total_payment': total_payment,
                'average_hourly_rate': average_hourly_rate,
                'objects_with_shifts': objects_with_shifts,
                'objects_with_timeslots': objects_with_timeslots
            }
            
        except Exception as e:
            logger.error(f"Error getting calendar stats for user {user_telegram_id}: {e}", exc_info=True)
            return {}
