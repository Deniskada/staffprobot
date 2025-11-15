"""Celery задачи для работы со сменами."""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List
from celery import Task
from decimal import Decimal, ROUND_HALF_UP

from core.celery.celery_app import celery_app
from core.logging.logger import logger
from core.cache.cache_service import CacheService
import pytz


class ShiftTask(Task):
    """Базовый класс для задач смен."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Обработка ошибок задач."""
        logger.error(
            f"Shift task failed: {self.name} (task_id: {task_id}, error: {str(exc)})"
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Обработка успешного выполнения."""
        logger.info(
            f"Shift task completed: {self.name} (task_id: {task_id})"
        )


@celery_app.task(base=ShiftTask, bind=True)
def auto_close_shifts(self):
    """Автоматическое закрытие просроченных смен."""
    try:
        import asyncio
        from core.database.session import get_async_session
        from datetime import datetime, time, timedelta
        from sqlalchemy import select, and_
        from domain.entities.shift import Shift
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.object import Object
        from domain.entities.time_slot import TimeSlot
        from sqlalchemy.orm import selectinload
        
        async def _auto_close_shifts():
            async with get_async_session() as session:
                now_utc = datetime.now(pytz.UTC)
                closed_count = 0
                errors = []
                
                # 1. Спонтанные смены: eager-load object
                from domain.entities.org_structure import OrgStructureUnit
                active_shifts_query = (
                    select(Shift)
                    .options(
                        selectinload(Shift.object).selectinload(Object.org_unit)
                    )
                    .join(Object)
                    .filter(
                        and_(
                            Shift.status == 'active',
                            Shift.start_time < now_utc
                        )
                    )
                )
                
                active_shifts_result = await session.execute(active_shifts_query)
                active_shifts = active_shifts_result.scalars().all()
                
                for shift in active_shifts:
                    try:
                        end_time_utc = None
                        planned_end_utc = None
                        obj = shift.object
                        tz_name = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                        obj_tz = pytz.timezone(tz_name)
                        start_local = shift.start_time.astimezone(obj_tz) if getattr(shift.start_time, 'tzinfo', None) else obj_tz.localize(shift.start_time)
                        
                        # Для запланированных смен (is_planned=True) используем время из тайм-слота
                        if shift.is_planned and shift.time_slot_id:
                            timeslot_query = select(TimeSlot).filter(TimeSlot.id == shift.time_slot_id)
                            timeslot_result = await session.execute(timeslot_query)
                            timeslot = timeslot_result.scalar_one_or_none()
                            if timeslot and timeslot.end_time:
                                end_local = datetime.combine(start_local.date(), timeslot.end_time)
                                end_local = obj_tz.localize(end_local)
                                planned_end_utc = end_local.astimezone(pytz.UTC)
                                end_time_utc = planned_end_utc
                                logger.info(f"Shift {shift.id}: using timeslot end_time {timeslot.end_time}")
                        
                        # Для спонтанных смен используем closing_time объекта
                        if planned_end_utc is None and obj and obj.closing_time:
                            end_local = datetime.combine(start_local.date(), obj.closing_time)
                            end_local = obj_tz.localize(end_local)
                            planned_end_utc = end_local.astimezone(pytz.UTC)
                            end_time_utc = planned_end_utc
                            logger.info(f"Shift {shift.id}: using object closing_time {obj.closing_time}")

                        # Проверяем, совпадает ли planned_end с closing_time объекта
                        planned_end_matches_closing_time = False
                        planned_end_time = None
                        if planned_end_utc and obj and obj.closing_time:
                            planned_end_local = planned_end_utc.astimezone(obj_tz)
                            planned_end_time = planned_end_local.time()
                            if planned_end_time == obj.closing_time:
                                planned_end_matches_closing_time = True
                                logger.debug(f"Shift {shift.id}: planned_end ({planned_end_time}) matches object closing_time ({obj.closing_time})")

                        # Если planned_end совпадает с closing_time объекта, используем auto_close_minutes
                        should_close = False
                        close_at_time = None
                        if planned_end_matches_closing_time and obj and obj.auto_close_minutes:
                            # Проверяем, прошло ли >= auto_close_minutes со времени planned_end
                            auto_close_deadline = planned_end_utc + timedelta(minutes=obj.auto_close_minutes)
                            if now_utc >= auto_close_deadline:
                                should_close = True
                                close_at_time = planned_end_utc  # Используем время закрытия объекта, а не текущее время
                                logger.info(
                                    f"Shift {shift.id}: auto-close condition met (planned_end={planned_end_utc}, "
                                    f"auto_close_minutes={obj.auto_close_minutes}, deadline={auto_close_deadline}, now={now_utc})"
                                )
                        elif planned_end_time and obj and obj.closing_time and obj.auto_close_minutes:
                            # Если planned_end != closing_time, проверяем: ждём до closing_time + auto_close_minutes
                            # Затем закрываем с end_time = planned_end
                            closing_time_local = datetime.combine(planned_end_local.date(), obj.closing_time)
                            closing_time_local = obj_tz.localize(closing_time_local)
                            closing_time_utc = closing_time_local.astimezone(pytz.UTC)
                            auto_close_deadline = closing_time_utc + timedelta(minutes=obj.auto_close_minutes)
                            
                            logger.debug(
                                f"Shift {shift.id}: planned_end ({planned_end_time}) != closing_time ({obj.closing_time}), "
                                f"waiting until {auto_close_deadline} (closing_time + auto_close_minutes={obj.auto_close_minutes})"
                            )
                            
                            if now_utc >= auto_close_deadline:
                                should_close = True
                                close_at_time = planned_end_utc  # Используем planned_end, а не closing_time
                                logger.info(
                                    f"Shift {shift.id}: auto-close condition met for non-matching shift "
                                    f"(planned_end={planned_end_utc}, closing_time={obj.closing_time}, "
                                    f"auto_close_minutes={obj.auto_close_minutes}, deadline={auto_close_deadline}, now={now_utc})"
                                )
                        elif end_time_utc and now_utc >= end_time_utc:
                            # Для остальных смен (без auto_close_minutes или без planned_end) - стандартная логика
                            should_close = True
                            close_at_time = end_time_utc

                        if should_close and close_at_time:
                            duration = close_at_time - shift.start_time
                            total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                            total_hours = total_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            total_payment = None
                            if shift.hourly_rate is not None:
                                rate_decimal = Decimal(shift.hourly_rate)
                                total_payment = (total_hours * rate_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            
                            shift.end_time = close_at_time  # Используем close_at_time (может быть planned_end для смен с closing_time)
                            shift.status = 'completed'
                            shift.total_hours = float(total_hours)
                            shift.total_payment = float(total_payment) if total_payment is not None else None
                            
                            closed_count += 1
                            shift_type = "planned" if shift.is_planned else "spontaneous"
                            if planned_end_matches_closing_time:
                                time_source = f"object closing_time (auto_close_minutes={obj.auto_close_minutes})"
                            else:
                                time_source = "timeslot" if (shift.is_planned and shift.time_slot_id) else "object closing_time"
                            logger.info(f"Auto-closed {shift_type} shift {shift.id} at {close_at_time} ({time_source})")
                            
                            # Этап 4: Автооткрытие следующей запланированной смены (для фактических Shift)
                            if shift.is_planned and shift.schedule_id and shift.time_slot_id:
                                try:
                                    from domain.entities.user import User
                                    from sqlalchemy import func
                                    
                                    # Обновляем статус текущего schedule
                                    schedule_query = select(ShiftSchedule).filter(ShiftSchedule.id == shift.schedule_id)
                                    schedule_result = await session.execute(schedule_query)
                                    current_schedule = schedule_result.scalar_one_or_none()
                                    
                                    if current_schedule:
                                        current_schedule.status = 'completed'
                                        session.add(current_schedule)
                                        
                                        # Проверка 1: Есть ли следующая запланированная смена в этот же день?
                                        next_schedule_query = (
                                            select(ShiftSchedule)
                                            .options(selectinload(ShiftSchedule.time_slot))
                                            .filter(
                                                and_(
                                                    ShiftSchedule.user_id == shift.user_id,
                                                    ShiftSchedule.status == 'planned',
                                                    func.date(ShiftSchedule.planned_start) == close_at_time.date(),
                                                    ShiftSchedule.id != shift.schedule_id
                                                )
                                            )
                                            .order_by(ShiftSchedule.planned_start)
                                        )
                                        
                                        # Допфильтр: тот же объект и точное совпадение времени (planned_start == конец закрытой)
                                        next_schedule_query = next_schedule_query.filter(
                                            and_(
                                                ShiftSchedule.object_id == shift.object_id,
                                                ShiftSchedule.planned_start == close_at_time
                                            )
                                        ).limit(1)
                                        next_schedule_result = await session.execute(next_schedule_query)
                                        next_schedule = next_schedule_result.scalars().first()
                                        
                                        if next_schedule and next_schedule.time_slot:
                                            # Проверка 2: Время начала следующей = времени окончания текущей?
                                            prev_timeslot_query = select(TimeSlot).filter(TimeSlot.id == shift.time_slot_id)
                                            prev_timeslot_result = await session.execute(prev_timeslot_query)
                                            prev_timeslot = prev_timeslot_result.scalar_one_or_none()
                                            
                                            next_timeslot = next_schedule.time_slot
                                            
                                            if prev_timeslot and prev_timeslot.end_time == next_timeslot.start_time:
                                                # Время совпадает! Открываем следующую смену
                                                
                                                # Получаем пользователя
                                                user_query = select(User).filter(User.id == shift.user_id)
                                                user_result = await session.execute(user_query)
                                                user = user_result.scalar_one_or_none()
                                                
                                                if user and shift.start_coordinates:
                                                    # Вычисляем planned_start для новой смены
                                                    # Используем late_threshold_minutes из объекта, без обхода иерархии
                                                    late_threshold_minutes = 0
                                                    if not obj.inherit_late_settings and obj.late_threshold_minutes is not None:
                                                        late_threshold_minutes = obj.late_threshold_minutes
                                                    
                                                    base_time = datetime.combine(next_timeslot.slot_date, next_timeslot.start_time)
                                                    base_time = obj_tz.localize(base_time)
                                                    start_time_utc = base_time.astimezone(pytz.UTC)
                                                    planned_start = base_time + timedelta(minutes=late_threshold_minutes)
                                                    
                                                    new_shift = Shift(
                                                        user_id=shift.user_id,
                                                        object_id=next_schedule.object_id,
                                                        start_time=start_time_utc,
                                                        actual_start=start_time_utc,
                                                        planned_start=planned_start,
                                                        status='active',
                                                        start_coordinates=shift.start_coordinates,
                                                        hourly_rate=next_schedule.hourly_rate,
                                                        time_slot_id=next_schedule.time_slot_id,
                                                        schedule_id=next_schedule.id,
                                                        is_planned=True
                                                    )
                                                    
                                                    session.add(new_shift)
                                                    await session.flush()  # Получаем new_shift.id
                                                    
                                                    # Синхронизация статусов при открытии смены из расписания
                                                    from shared.services.shift_status_sync_service import ShiftStatusSyncService
                                                    sync_service = ShiftStatusSyncService(session)
                                                    await sync_service.sync_on_shift_open(
                                                        new_shift,
                                                        actor_id=shift.user_id,
                                                        actor_role="system",
                                                        source="celery",
                                                        payload={
                                                            "auto_opened": True,
                                                            "prev_shift_id": shift.id,
                                                        },
                                                    )
                                                    
                                                    logger.info(
                                                        f"Auto-opened consecutive shift (from Shift): user_id={shift.user_id}, "
                                                        f"user_telegram_id={user.telegram_id}, "
                                                        f"prev_shift_id={shift.id}, next_schedule_id={next_schedule.id}, "
                                                        f"prev_time={prev_timeslot.start_time}-{prev_timeslot.end_time}, "
                                                        f"next_time={next_timeslot.start_time}-{next_timeslot.end_time}, "
                                                        f"object_id={next_schedule.object_id}"
                                                    )
                                                    
                                                else:
                                                    logger.debug(f"User or coordinates not found for auto-opening: shift_id={shift.id}")
                                            else:
                                                logger.debug(f"Time mismatch for consecutive shifts: prev_end={prev_timeslot.end_time if prev_timeslot else None}, next_start={next_timeslot.start_time}")
                                        else:
                                            logger.debug(f"No next planned shift found for user_id={shift.user_id} on date={close_at_time.date()}")
                                    
                                except Exception as e:
                                    logger.error(f"Error auto-opening consecutive shift for Shift {shift.id}: {e}")
                                    # Не прерываем основной процесс
                    except Exception as e:
                        error_msg = f"Error auto-closing spontaneous shift {shift.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # 2. Запланированные: eager-load object
                confirmed_schedules_query = (
                    select(ShiftSchedule)
                    .options(
                        selectinload(ShiftSchedule.object).selectinload(Object.org_unit)
                    )
                    .join(Object)
                    .filter(
                        and_(
                            ShiftSchedule.status.in_(['planned', 'confirmed']),  # confirmed - legacy, оставляем для совместимости
                            ShiftSchedule.planned_start < now_utc,
                            ShiftSchedule.auto_closed == False
                        )
                    )
                )
                
                confirmed_schedules_result = await session.execute(confirmed_schedules_query)
                confirmed_schedules = confirmed_schedules_result.scalars().all()
                
                for schedule in confirmed_schedules:
                    try:
                        planned_end_utc = None
                        end_time_utc = None
                        obj = schedule.object
                        tz_name = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                        obj_tz = pytz.timezone(tz_name)

                        # Локальная дата по planned_start в часовом поясе объекта
                        start_local = schedule.planned_start.astimezone(obj_tz) if getattr(schedule.planned_start, 'tzinfo', None) else obj_tz.localize(schedule.planned_start)

                        # 1) Конец тайм-слота (приоритетно)
                        if schedule.time_slot_id:
                            timeslot_query = select(TimeSlot).filter(TimeSlot.id == schedule.time_slot_id)
                            timeslot_result = await session.execute(timeslot_query)
                            timeslot = timeslot_result.scalar_one_or_none()
                            if timeslot and timeslot.end_time:
                                end_local = datetime.combine(start_local.date(), timeslot.end_time)
                                end_local = obj_tz.localize(end_local)
                                planned_end_utc = end_local.astimezone(pytz.UTC)
                                end_time_utc = planned_end_utc

                        # 2) Режим работы объекта (fallback)
                        if planned_end_utc is None and obj and obj.closing_time:
                            end_local = datetime.combine(start_local.date(), obj.closing_time)
                            end_local = obj_tz.localize(end_local)
                            planned_end_utc = end_local.astimezone(pytz.UTC)
                            end_time_utc = planned_end_utc

                        # 3) auto_close_minutes (в крайнем случае от planned_start)
                        if planned_end_utc is None and obj and getattr(obj, 'auto_close_minutes', 0) > 0:
                            planned_end_utc = (schedule.planned_start + timedelta(minutes=obj.auto_close_minutes))
                            end_time_utc = planned_end_utc

                        # Проверяем, совпадает ли planned_end с closing_time объекта
                        planned_end_matches_closing_time = False
                        planned_end_time = None
                        planned_end_local = None
                        if planned_end_utc and obj and obj.closing_time:
                            planned_end_local = planned_end_utc.astimezone(obj_tz)
                            planned_end_time = planned_end_local.time()
                            if planned_end_time == obj.closing_time:
                                planned_end_matches_closing_time = True
                                logger.debug(f"Schedule {schedule.id}: planned_end ({planned_end_time}) matches object closing_time ({obj.closing_time})")

                        # Если planned_end совпадает с closing_time объекта, используем auto_close_minutes
                        should_close = False
                        close_at_time = None
                        if planned_end_matches_closing_time and obj and obj.auto_close_minutes:
                            # Проверяем, прошло ли >= auto_close_minutes со времени planned_end
                            auto_close_deadline = planned_end_utc + timedelta(minutes=obj.auto_close_minutes)
                            if now_utc >= auto_close_deadline:
                                should_close = True
                                close_at_time = planned_end_utc  # Используем время закрытия объекта, а не текущее время
                                logger.info(
                                    f"Schedule {schedule.id}: auto-close condition met (planned_end={planned_end_utc}, "
                                    f"auto_close_minutes={obj.auto_close_minutes}, deadline={auto_close_deadline}, now={now_utc})"
                                )
                        elif planned_end_time and planned_end_local and obj and obj.closing_time and obj.auto_close_minutes:
                            # Если planned_end != closing_time, проверяем: ждём до closing_time + auto_close_minutes
                            # Затем закрываем с planned_end = planned_end
                            closing_time_local = datetime.combine(planned_end_local.date(), obj.closing_time)
                            closing_time_local = obj_tz.localize(closing_time_local)
                            closing_time_utc = closing_time_local.astimezone(pytz.UTC)
                            auto_close_deadline = closing_time_utc + timedelta(minutes=obj.auto_close_minutes)
                            
                            logger.debug(
                                f"Schedule {schedule.id}: planned_end ({planned_end_time}) != closing_time ({obj.closing_time}), "
                                f"waiting until {auto_close_deadline} (closing_time + auto_close_minutes={obj.auto_close_minutes})"
                            )
                            
                            if now_utc >= auto_close_deadline:
                                should_close = True
                                close_at_time = planned_end_utc  # Используем planned_end, а не closing_time
                                logger.info(
                                    f"Schedule {schedule.id}: auto-close condition met for non-matching shift "
                                    f"(planned_end={planned_end_utc}, closing_time={obj.closing_time}, "
                                    f"auto_close_minutes={obj.auto_close_minutes}, deadline={auto_close_deadline}, now={now_utc})"
                                )
                        elif end_time_utc and now_utc >= end_time_utc:
                            # Для остальных смен (без auto_close_minutes или без planned_end) - стандартная логика
                            should_close = True
                            close_at_time = end_time_utc

                        if should_close and close_at_time:
                            duration = close_at_time - schedule.planned_start
                            total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                            total_hours = total_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            total_payment = None
                            if schedule.hourly_rate is not None:
                                rate_decimal = Decimal(schedule.hourly_rate)
                                total_payment = (total_hours * rate_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            
                            schedule.status = 'completed'
                            schedule.planned_end = close_at_time  # Используем close_at_time (может быть planned_end для смен с closing_time)
                            schedule.auto_closed = True
                            # Note: schedule doesn't store totals; actual totals are on real Shift. Kept here if needed elsewhere.
                            
                            closed_count += 1
                            if planned_end_matches_closing_time:
                                time_source = f"object closing_time (auto_close_minutes={obj.auto_close_minutes})"
                            else:
                                time_source = "timeslot/object closing time"
                            logger.info(f"Auto-closed planned shift {schedule.id} at {close_at_time} ({time_source})")
                            
                            # Этап 4: Автооткрытие следующей запланированной смены
                            try:
                                from domain.entities.user import User
                                from sqlalchemy import func
                                
                                # Проверка 1: Есть ли следующая запланированная смена в этот же день?
                                next_schedule_query = (
                                    select(ShiftSchedule)
                                    .options(selectinload(ShiftSchedule.time_slot))
                                    .filter(
                                        and_(
                                            ShiftSchedule.user_id == schedule.user_id,
                                            ShiftSchedule.status == 'planned',
                                            func.date(ShiftSchedule.planned_start) == close_at_time.date(),
                                            ShiftSchedule.id != schedule.id
                                        )
                                    )
                                    .order_by(ShiftSchedule.planned_start)
                                )
                                
                                # Допфильтр: тот же объект и точное совпадение времени (planned_start == конец закрытой)
                                next_schedule_query = next_schedule_query.filter(
                                    and_(
                                        ShiftSchedule.object_id == schedule.object_id,
                                        ShiftSchedule.planned_start == close_at_time
                                    )
                                ).limit(1)
                                next_schedule_result = await session.execute(next_schedule_query)
                                next_schedule = next_schedule_result.scalars().first()
                                
                                if next_schedule and next_schedule.time_slot and schedule.time_slot_id:
                                    # Проверка 2: Время начала следующей = времени окончания текущей?
                                    prev_timeslot_query = select(TimeSlot).filter(TimeSlot.id == schedule.time_slot_id)
                                    prev_timeslot_result = await session.execute(prev_timeslot_query)
                                    prev_timeslot = prev_timeslot_result.scalar_one_or_none()
                                    
                                    next_timeslot = next_schedule.time_slot
                                    
                                    if prev_timeslot and prev_timeslot.end_time == next_timeslot.start_time:
                                        # Время совпадает! Открываем следующую смену
                                        
                                        # Получаем координаты из ТОЛЬКО ЧТО закрытой смены
                                        prev_shift_query = select(Shift).filter(
                                            and_(
                                                Shift.schedule_id == schedule.id,
                                                Shift.status == 'completed'
                                            )
                                        )
                                        prev_shift_result = await session.execute(prev_shift_query)
                                        prev_shift = prev_shift_result.scalar_one_or_none()
                                        
                                        if prev_shift and prev_shift.start_coordinates:
                                            # Получаем пользователя
                                            user_query = select(User).filter(User.id == schedule.user_id)
                                            user_result = await session.execute(user_query)
                                            user = user_result.scalar_one_or_none()
                                            
                                            if user:
                                                # Вычисляем planned_start для новой смены
                                                # Используем late_threshold_minutes из объекта, без обхода иерархии
                                                late_threshold_minutes = 0
                                                if not obj.inherit_late_settings and obj.late_threshold_minutes is not None:
                                                    late_threshold_minutes = obj.late_threshold_minutes
                                                
                                                base_time = datetime.combine(next_timeslot.slot_date, next_timeslot.start_time)
                                                base_time = obj_tz.localize(base_time)
                                                start_time_utc = base_time.astimezone(pytz.UTC)
                                                planned_start = base_time + timedelta(minutes=late_threshold_minutes)
                                                
                                                new_shift = Shift(
                                                    user_id=schedule.user_id,
                                                    object_id=next_schedule.object_id,
                                                    start_time=start_time_utc,
                                                    actual_start=start_time_utc,
                                                    planned_start=planned_start,
                                                    status='active',
                                                    start_coordinates=prev_shift.start_coordinates,
                                                    hourly_rate=next_schedule.hourly_rate,
                                                    time_slot_id=next_schedule.time_slot_id,
                                                    schedule_id=next_schedule.id,
                                                    is_planned=True
                                                )
                                                
                                                session.add(new_shift)
                                                
                                                # Обновляем статус следующего расписания
                                                next_schedule.status = 'in_progress'
                                                session.add(next_schedule)
                                                
                                                logger.info(
                                                    f"Auto-opened consecutive shift: user_id={schedule.user_id}, "
                                                    f"user_telegram_id={user.telegram_id}, "
                                                    f"prev_schedule_id={schedule.id}, next_schedule_id={next_schedule.id}, "
                                                    f"prev_time={prev_timeslot.start_time}-{prev_timeslot.end_time}, "
                                                    f"next_time={next_timeslot.start_time}-{next_timeslot.end_time}, "
                                                    f"object_id={next_schedule.object_id}"
                                                )
                                                
                                            else:
                                                logger.warning(f"User not found for auto-opening consecutive shift: user_id={schedule.user_id}")
                                        else:
                                            logger.debug(f"No previous shift or coordinates for auto-opening consecutive shift: schedule_id={schedule.id}")
                                    else:
                                        logger.debug(f"Time mismatch for consecutive shifts: prev_end={prev_timeslot.end_time if prev_timeslot else None}, next_start={next_timeslot.start_time}")
                                else:
                                    logger.debug(f"No next planned shift found for user_id={schedule.user_id} on date={end_time_utc.date()}")
                                    
                            except Exception as e:
                                logger.error(f"Error auto-opening consecutive shift for schedule {schedule.id}: {e}")
                                # Не прерываем основной процесс
                    except Exception as e:
                        error_msg = f"Error auto-closing planned shift {schedule.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # Сохраняем изменения смен (async)
                await session.commit()
                
                logger.info(f"Auto-closed {closed_count} shifts")
                
                # 3. Закрываем ObjectOpening для объектов без активных смен
                closed_openings_count = 0
                try:
                    from shared.services.object_opening_service import ObjectOpeningService
                    from domain.entities.object_opening import ObjectOpening
                    
                    opening_service = ObjectOpeningService(session)
                    
                    # Собираем уникальные object_id из закрытых смен
                    closed_object_ids = set()
                    for shift in active_shifts:
                        if shift.status == 'completed':  # Только если смена была закрыта
                            closed_object_ids.add(shift.object_id)
                    
                    for schedule in confirmed_schedules:
                        if schedule.status == 'completed':  # Только если смена была закрыта
                            closed_object_ids.add(schedule.object_id)
                    
                    logger.info(f"Checking {len(closed_object_ids)} objects for auto-closing ObjectOpening")
                    
                    # Для каждого объекта проверяем активные смены
                    for object_id in closed_object_ids:
                        active_count = await opening_service.get_active_shifts_count(object_id)
                        
                        if active_count == 0:
                            # Закрываем ObjectOpening
                            opening = await opening_service.get_active_opening(object_id)
                            if opening:
                                opening.closed_at = now_utc.replace(tzinfo=None)
                                opening.closed_by = None  # Автоматическое закрытие
                                closed_openings_count += 1
                                logger.info(f"Auto-closed ObjectOpening {opening.id} for object {object_id} - no active shifts")
                    
                    if closed_openings_count > 0:
                        await session.commit()
                        logger.info(f"Auto-closed {closed_openings_count} ObjectOpenings")
                        
                except Exception as e:
                    logger.error(f"Error auto-closing ObjectOpenings: {e}")
                    # Не прерываем выполнение задачи
                
                return {
                    "success": True,
                    "closed_count": closed_count,
                    "closed_openings_count": closed_openings_count,
                    "errors": errors
                }
                
        # Запускаем async-функцию корректно
        result = asyncio.run(_auto_close_shifts())
        return result
        
    except Exception as e:
        logger.error(f"Error in auto_close_shifts task: {e}")
        return 0


@celery_app.task(base=ShiftTask, bind=True)
def calculate_shift_payment(self, shift_id: int):
    """Асинхронный расчет оплаты за смену."""
    try:
        from core.database.session import DatabaseManager
        from apps.api.services.shift_service_db import ShiftServiceDB
        
        db_manager = DatabaseManager()
        
        async def _calculate_payment():
            async with db_manager.get_session() as session:
                shift_service = ShiftServiceDB(session)
                
                # Получаем смену
                shift = await shift_service.get_shift(shift_id)
                if not shift:
                    raise ValueError(f"Shift {shift_id} not found")
                
                # Рассчитываем оплату
                payment_data = await shift_service.calculate_payment(shift_id)
                
                # Обновляем смену с рассчитанными данными
                await shift_service.update_shift(shift_id, {
                    'total_hours': payment_data['total_hours'],
                    'total_payment': payment_data['total_payment']
                })
                
                # Инвалидируем кэш
                await CacheService.invalidate_shift_cache(shift_id, shift.user_id)
                
                return payment_data
        
        import asyncio
        payment_data = asyncio.run(_calculate_payment())
        
        logger.info(
            "Shift payment calculated",
            shift_id=shift_id,
            total_hours=payment_data['total_hours'],
            total_payment=payment_data['total_payment']
        )
        
        return payment_data
        
    except Exception as e:
        logger.error(f"Failed to calculate shift payment for {shift_id}: {e}")
        raise


@celery_app.task(base=ShiftTask, bind=True)
def validate_shift_location(self, shift_id: int, coordinates: str):
    """Асинхронная валидация геолокации смены."""
    try:
        from core.database.session import DatabaseManager
        from apps.api.services.shift_service_db import ShiftServiceDB
        from core.geolocation.distance_calculator import DistanceCalculator
        from core.geolocation.location_validator import LocationValidator
        
        db_manager = DatabaseManager()
        
        async def _validate_location():
            async with db_manager.get_session() as session:
                shift_service = ShiftServiceDB(session)
                
                # Получаем смену с объектом
                shift = await shift_service.get_shift_with_object(shift_id)
                if not shift:
                    raise ValueError(f"Shift {shift_id} not found")
                
                # Валидируем координаты
                location_validator = LocationValidator()
                if not location_validator.validate_coordinates(coordinates):
                    return {"valid": False, "error": "Invalid coordinates format"}
                
                # Рассчитываем расстояние
                distance_calculator = DistanceCalculator()
                object_coordinates = f"{shift.object.coordinates.x},{shift.object.coordinates.y}"
                
                distance = distance_calculator.calculate_distance(
                    coordinates, 
                    object_coordinates
                )
                
                max_distance = shift.object.max_distance_meters or 500
                is_valid = distance <= max_distance
                
                return {
                    "valid": is_valid,
                    "distance": distance,
                    "max_distance": max_distance,
                    "coordinates": coordinates,
                    "object_coordinates": object_coordinates
                }
        
        import asyncio
        validation_result = asyncio.run(_validate_location())
        
        logger.info(
            "Shift location validated",
            shift_id=shift_id,
            valid=validation_result['valid'],
            distance=validation_result.get('distance', 0)
        )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate shift location for {shift_id}: {e}")
        raise


@celery_app.task(base=ShiftTask, bind=True)
def cleanup_expired_shifts(self):
    """Очистка устаревших данных смен."""
    try:
        from core.database.session import DatabaseManager
        from apps.api.services.shift_service_db import ShiftServiceDB
        
        db_manager = DatabaseManager()
        
        async def _cleanup_shifts():
            async with db_manager.get_session() as session:
                shift_service = ShiftServiceDB(session)
                
                # Удаляем смены старше 1 года
                cutoff_date = datetime.now() - timedelta(days=365)
                deleted_count = await shift_service.delete_old_shifts(cutoff_date)
                
                # Очищаем связанный кэш
                await CacheService.clear_analytics_cache()
                
                return deleted_count
        
        import asyncio
        deleted_count = asyncio.run(_cleanup_shifts())
        
        logger.info(f"Cleaned up {deleted_count} expired shifts")
        return {"deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired shifts: {e}")
        raise


@celery_app.task(base=ShiftTask, bind=True)
def sync_shift_schedules(self):
    """Синхронизация запланированных смен с реальными сменами."""
    try:
        from core.database.session import DatabaseManager
        from apps.bot.services.schedule_service import ScheduleService
        from apps.api.services.shift_service_db import ShiftServiceDB
        
        db_manager = DatabaseManager()
        
        async def _sync_schedules():
            async with db_manager.get_session() as session:
                schedule_service = ScheduleService(session)
                shift_service = ShiftServiceDB(session)
                
                # Получаем запланированные смены на сегодня
                today = datetime.now().date()
                scheduled_shifts = await schedule_service.get_shifts_for_date(today)
                
                synced_count = 0
                for scheduled_shift in scheduled_shifts:
                    try:
                        # Проверяем, есть ли реальная смена для этого расписания
                        real_shift = await shift_service.get_shift_by_schedule_id(
                            scheduled_shift.id
                        )
                        
                        if not real_shift and scheduled_shift.planned_start <= datetime.now():
                            # Создаем напоминание о пропущенной смене
                            from core.celery.tasks.notification_tasks import send_shift_notification
                            send_shift_notification.delay(
                                user_id=scheduled_shift.user_id,
                                notification_type="missed_shift",
                                data={
                                    'schedule_id': scheduled_shift.id,
                                    'object_name': scheduled_shift.object.name if scheduled_shift.object else 'Unknown',
                                    'planned_start': scheduled_shift.planned_start.isoformat()
                                }
                            )
                            synced_count += 1
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to sync schedule {scheduled_shift.id}: {e}"
                        )
                
                return synced_count
        
        import asyncio
        synced_count = asyncio.run(_sync_schedules())
        
        logger.info(f"Synced {synced_count} shift schedules")
        return {"synced_count": synced_count}
        
    except Exception as e:
        logger.error(f"Failed to sync shift schedules: {e}")
        raise


@celery_app.task(base=ShiftTask, bind=True)
def plan_next_year_timeslots(self):
    """1 декабря — автогенерация тайм-слотов объектов на следующий год по графику работы."""
    try:
        from core.database.session import get_async_session
        from sqlalchemy import select, and_
        from domain.entities.object import Object
        from domain.entities.time_slot import TimeSlot
        from datetime import date, timedelta

        async def _plan_next_year():
            async with get_async_session() as session:
                next_year = date.today().year + 1
                start_date = date(next_year, 1, 1)
                end_date = date(next_year, 12, 31)

                objs_res = await session.execute(select(Object).where(Object.is_active == True))
                objects = objs_res.scalars().all()

                created_total = 0
                for obj in objects:
                    work_days_mask = getattr(obj, "work_days_mask", 31)
                    schedule_repeat_weeks = getattr(obj, "schedule_repeat_weeks", 1)

                    base_week_index = start_date.isocalendar().week
                    d = start_date

                    while d <= end_date:
                        dow_mask = 1 << (d.weekday())
                        if (work_days_mask & dow_mask) != 0:
                            week_index = d.isocalendar().week
                            if ((week_index - base_week_index) % schedule_repeat_weeks) == 0:
                                exists_res = await session.execute(
                                    select(TimeSlot).where(
                                        and_(
                                            TimeSlot.object_id == obj.id,
                                            TimeSlot.slot_date == d
                                        )
                                    )
                                )
                                if not exists_res.scalars().first():
                                    ts = TimeSlot(
                                        object_id=obj.id,
                                        slot_date=d,
                                        start_time=obj.opening_time,
                                        end_time=obj.closing_time,
                                        hourly_rate=float(obj.hourly_rate) if obj.hourly_rate else 0,
                                        is_active=True
                                    )
                                    session.add(ts)
                                    created_total += 1
                        d = d + timedelta(days=1)

                await session.commit()
                return created_total

        import asyncio
        created = asyncio.run(_plan_next_year())
        logger.info(f"Planned next year timeslots: created={created}")
        return created
    except Exception as e:
        logger.error(f"Error in plan_next_year_timeslots: {e}")
        return 0
