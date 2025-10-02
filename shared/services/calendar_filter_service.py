"""Универсальный сервис фильтрации данных календаря."""

import logging
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date, time, timedelta
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

logger = logging.getLogger(__name__)


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
            # Проверяем кэш
            cache_key = self._generate_cache_key(
                user_telegram_id, user_role, date_range_start, date_range_end, object_filter
            )
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for user {user_telegram_id}")
                return cached_data
            
            logger.info(f"Getting calendar data for user {user_telegram_id}, role {user_role}, period {date_range_start} to {date_range_end}")
            
            # Получаем доступные объекты
            accessible_objects = await self.object_access_service.get_accessible_objects(
                user_telegram_id, user_role
            )
            
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
            timeslots = self._update_timeslot_statuses(timeslots, shifts)
            
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
            
            # Сохраняем в кэш
            self._set_cache(cache_key, result, ttl_minutes=5)
            
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
    
    async def _get_timeslots(
        self,
        object_ids: List[int],
        date_range_start: date,
        date_range_end: date,
        accessible_objects: List[Dict[str, Any]]
    ) -> List[CalendarTimeslot]:
        """Получить тайм-слоты для объектов."""
        try:
            # Создаем словарь объектов для быстрого доступа
            objects_map = {obj['id']: obj for obj in accessible_objects}
            
            # Оптимизированный запрос с индексами
            timeslots_query = select(TimeSlot).options(
                selectinload(TimeSlot.object)
            ).where(
                and_(
                    TimeSlot.object_id.in_(object_ids),
                    TimeSlot.slot_date >= date_range_start,
                    TimeSlot.slot_date < date_range_end,
                    TimeSlot.is_active == True
                )
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
            
            timeslots_result = await self.db.execute(timeslots_query)
            timeslots = timeslots_result.scalars().all()
            
            calendar_timeslots = []
            for slot in timeslots:
                obj_info = objects_map.get(slot.object_id)
                if not obj_info:
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
            
            calendar_shifts = []
            
            # 1. Получаем фактические смены (активные и завершенные)
            actual_shifts = await self._get_actual_shifts(object_ids, date_range_start, date_range_end, objects_map)
            calendar_shifts.extend(actual_shifts)
            
            # 2. Получаем запланированные смены (только те, которые НЕ начались)
            # Исключаем те, для которых уже есть фактические смены
            actual_shift_ids = {shift.schedule_id for shift in actual_shifts if shift.schedule_id}
            planned_shifts = await self._get_planned_shifts(object_ids, date_range_start, date_range_end, objects_map, exclude_schedule_ids=actual_shift_ids)
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
                        filtered_planned_shifts.append(CalendarShift(
                            id=shift_schedule.id,
                            user_id=shift_schedule.user_id,
                            user_name=f"{shift_schedule.user.first_name or ''} {shift_schedule.user.last_name or ''}".strip(),
                            object_id=shift_schedule.object_id,
                            object_name=obj_info['name'],
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
        objects_map: Dict[int, Dict[str, Any]]
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
                    elif shift.status == "cancelled":
                        shift_type = ShiftType.CANCELLED
                    else:
                        shift_type = ShiftType.ACTIVE  # По умолчанию
                    
                    calendar_shifts.append(CalendarShift(
                        id=shift.id,
                        user_id=shift.user_id,
                        user_name=f"{shift.user.first_name or ''} {shift.user.last_name or ''}".strip(),
                        object_id=shift.object_id,
                        object_name=obj_info['name'],
                        time_slot_id=shift.time_slot_id,
                        start_time=shift.start_time,
                        end_time=shift.end_time,
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
    
    def _update_timeslot_statuses(
        self,
        timeslots: List[CalendarTimeslot],
        shifts: List[CalendarShift]
    ) -> List[CalendarTimeslot]:
        """Обновить статусы тайм-слотов на основе смен."""
        try:
            # Группируем смены по тайм-слотам
            shifts_by_timeslot = {}
            for shift in shifts:
                if shift.time_slot_id:
                    if shift.time_slot_id not in shifts_by_timeslot:
                        shifts_by_timeslot[shift.time_slot_id] = []
                    shifts_by_timeslot[shift.time_slot_id].append(shift)
            
            # Обновляем статусы тайм-слотов
            for timeslot in timeslots:
                timeslot_shifts = shifts_by_timeslot.get(timeslot.id, [])
                
                # Считаем только активные смены (не отмененные)
                active_shifts = [s for s in timeslot_shifts if s.status != ShiftStatus.CANCELLED]
                timeslot.current_employees = len(active_shifts)
                timeslot.available_slots = max(0, timeslot.max_employees - timeslot.current_employees)
                
                # Определяем статус
                if timeslot.current_employees == 0:
                    timeslot.status = TimeslotStatus.AVAILABLE
                elif timeslot.current_employees < timeslot.max_employees:
                    timeslot.status = TimeslotStatus.PARTIALLY_FILLED
                else:
                    timeslot.status = TimeslotStatus.FULLY_FILLED
            
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
