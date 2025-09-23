"""Celery задачи для работы со сменами."""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List
from celery import Task

from core.celery.celery_app import celery_app
from core.logging.logger import logger
from core.cache.cache_service import CacheService


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
        
        async def _auto_close_shifts():
            async with get_async_session() as session:
                now = datetime.now()
                closed_count = 0
                errors = []
                
                # 1. Обрабатываем СПОНТАННЫЕ смены (Shift) - закрываем по времени работы объекта
                active_shifts_query = select(Shift).join(Object).filter(
                    and_(
                        Shift.status == 'active',
                        Shift.start_time < now
                    )
                )
                
                active_shifts_result = await session.execute(active_shifts_query)
                active_shifts = active_shifts_result.scalars().all()
                
                for shift in active_shifts:
                    try:
                        end_time = None
                        # Время закрытия по режиму объекта в день начала смены
                        if shift.object and shift.object.closing_time:
                            end_time = datetime.combine(shift.start_time.date(), shift.object.closing_time)
                        
                        if end_time and now >= end_time:
                            duration = end_time - shift.start_time
                            total_hours = duration.total_seconds() / 3600
                            total_payment = total_hours * shift.hourly_rate if shift.hourly_rate else None
                            
                            shift.end_time = end_time
                            shift.status = 'completed'
                            shift.total_hours = total_hours
                            shift.total_payment = total_payment
                            
                            closed_count += 1
                            logger.info(f"Auto-closed spontaneous shift {shift.id} at {end_time} (object closing time)")
                    except Exception as e:
                        error_msg = f"Error auto-closing spontaneous shift {shift.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                # 2. Обрабатываем ЗАПЛАНИРОВАННЫЕ смены (ShiftSchedule) - закрываем по времени окончания тайм-слота
                confirmed_schedules_query = select(ShiftSchedule).join(Object).filter(
                    and_(
                        ShiftSchedule.status == 'confirmed',
                        ShiftSchedule.planned_start < now,
                        ShiftSchedule.auto_closed == False
                    )
                )
                
                confirmed_schedules_result = await session.execute(confirmed_schedules_query)
                confirmed_schedules = confirmed_schedules_result.scalars().all()
                
                for schedule in confirmed_schedules:
                    try:
                        end_time = None
                        # 1) Конец тайм-слота
                        if schedule.time_slot_id:
                            timeslot_query = select(TimeSlot).filter(TimeSlot.id == schedule.time_slot_id)
                            timeslot_result = await session.execute(timeslot_query)
                            timeslot = timeslot_result.scalar_one_or_none()
                            if timeslot and timeslot.end_time:
                                end_time = datetime.combine(schedule.planned_start.date(), timeslot.end_time)
                        # 2) Режим работы объекта
                        if not end_time and schedule.object and schedule.object.closing_time:
                            end_time = datetime.combine(schedule.planned_start.date(), schedule.object.closing_time)
                        # 3) Если указан auto_close_minutes у объекта
                        if not end_time and schedule.object and getattr(schedule.object, 'auto_close_minutes', 0) > 0:
                            end_time = schedule.planned_start + timedelta(minutes=schedule.object.auto_close_minutes)
                        
                        # Без fallback на полночь — не закрываем в 00:00
                        if end_time and now >= end_time:
                            duration = end_time - schedule.planned_start
                            total_hours = duration.total_seconds() / 3600
                            total_payment = total_hours * schedule.hourly_rate if schedule.hourly_rate else None
                            
                            schedule.status = 'completed'
                            schedule.planned_end = end_time
                            schedule.auto_closed = True
                            
                            closed_count += 1
                            logger.info(f"Auto-closed planned shift {schedule.id} at {end_time} (timeslot/object closing time)")
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
