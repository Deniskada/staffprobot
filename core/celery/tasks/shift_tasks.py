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
                active_shifts_query = (
                    select(Shift)
                    .options(selectinload(Shift.object))
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
                                end_time_utc = end_local.astimezone(pytz.UTC)
                                logger.info(f"Shift {shift.id}: using timeslot end_time {timeslot.end_time}")
                        
                        # Для спонтанных смен используем closing_time объекта
                        if end_time_utc is None and obj and obj.closing_time:
                            end_local = datetime.combine(start_local.date(), obj.closing_time)
                            end_local = obj_tz.localize(end_local)
                            end_time_utc = end_local.astimezone(pytz.UTC)
                            logger.info(f"Shift {shift.id}: using object closing_time {obj.closing_time}")

                        if end_time_utc and now_utc >= end_time_utc:
                            duration = end_time_utc - shift.start_time
                            total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                            total_hours = total_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            total_payment = None
                            if shift.hourly_rate is not None:
                                rate_decimal = Decimal(shift.hourly_rate)
                                total_payment = (total_hours * rate_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            
                            shift.end_time = end_time_utc
                            shift.status = 'completed'
                            shift.total_hours = float(total_hours)
                            shift.total_payment = float(total_payment) if total_payment is not None else None
                            
                            # Создаем корректировки начислений (Phase 4A)
                            from shared.services.payroll_adjustment_service import PayrollAdjustmentService
                            from shared.services.late_penalty_calculator import LatePenaltyCalculator
                            
                            adjustment_service = PayrollAdjustmentService(session)
                            late_penalty_calc = LatePenaltyCalculator(session)
                            
                            # 1. Создать базовую оплату за смену
                            await adjustment_service.create_shift_base_adjustment(
                                shift=shift,
                                employee_id=shift.user_id,
                                object_id=shift.object_id,
                                created_by=shift.user_id  # Для авто-закрытия - сотрудник
                            )
                            
                            # 2. Проверить и создать штраф за опоздание
                            late_minutes, penalty_amount = await late_penalty_calc.calculate_late_penalty(
                                shift=shift,
                                obj=obj
                            )
                            
                            if penalty_amount > 0:
                                await adjustment_service.create_late_start_adjustment(
                                    shift=shift,
                                    late_minutes=late_minutes,
                                    penalty_amount=penalty_amount,
                                    created_by=shift.user_id
                                )
                            
                            closed_count += 1
                            shift_type = "planned" if shift.is_planned else "spontaneous"
                            time_source = "timeslot" if (shift.is_planned and shift.time_slot_id) else "object closing_time"
                            logger.info(f"Auto-closed {shift_type} shift {shift.id} at {end_time_utc} ({time_source})")
                    except Exception as e:
                        error_msg = f"Error auto-closing spontaneous shift {shift.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # 2. Запланированные: eager-load object
                confirmed_schedules_query = (
                    select(ShiftSchedule)
                    .options(selectinload(ShiftSchedule.object))
                    .join(Object)
                    .filter(
                        and_(
                            ShiftSchedule.status == 'confirmed',
                            ShiftSchedule.planned_start < now_utc,
                            ShiftSchedule.auto_closed == False
                        )
                    )
                )
                
                confirmed_schedules_result = await session.execute(confirmed_schedules_query)
                confirmed_schedules = confirmed_schedules_result.scalars().all()
                
                for schedule in confirmed_schedules:
                    try:
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
                                end_time_utc = end_local.astimezone(pytz.UTC)

                        # 2) Режим работы объекта (fallback)
                        if end_time_utc is None and obj and obj.closing_time:
                            end_local = datetime.combine(start_local.date(), obj.closing_time)
                            end_local = obj_tz.localize(end_local)
                            end_time_utc = end_local.astimezone(pytz.UTC)

                        # 3) auto_close_minutes (в крайнем случае от planned_start)
                        if end_time_utc is None and obj and getattr(obj, 'auto_close_minutes', 0) > 0:
                            end_time_utc = (schedule.planned_start + timedelta(minutes=obj.auto_close_minutes))

                        if end_time_utc and now_utc >= end_time_utc:
                            duration = end_time_utc - schedule.planned_start
                            total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                            total_hours = total_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            total_payment = None
                            if schedule.hourly_rate is not None:
                                rate_decimal = Decimal(schedule.hourly_rate)
                                total_payment = (total_hours * rate_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            
                            schedule.status = 'completed'
                            schedule.planned_end = end_time_utc
                            schedule.auto_closed = True
                            # Note: schedule doesn't store totals; actual totals are on real Shift. Kept here if needed elsewhere.
                            
                            closed_count += 1
                            logger.info(f"Auto-closed planned shift {schedule.id} at {end_time_utc} (timeslot/object closing time)")
                    except Exception as e:
                        error_msg = f"Error auto-closing planned shift {schedule.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # Сохраняем изменения (async)
                await session.commit()
                
                logger.info(f"Auto-closed {closed_count} shifts")
                return {
                    "success": True,
                    "closed_count": closed_count,
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
