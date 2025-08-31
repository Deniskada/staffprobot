"""Celery задачи для работы со сменами."""

from datetime import datetime, timedelta
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
            f"Shift task failed: {self.name}",
            task_id=task_id,
            error=str(exc),
            args=args,
            kwargs=kwargs
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Обработка успешного выполнения."""
        logger.info(
            f"Shift task completed: {self.name}",
            task_id=task_id,
            result=retval
        )


@celery_app.task(base=ShiftTask, bind=True)
def auto_close_shifts(self):
    """Автоматическое закрытие просроченных смен."""
    try:
        from core.database.session import DatabaseManager
        from apps.bot.services.time_slot_service import TimeSlotService
        
        db_manager = DatabaseManager()
        
        async def _auto_close_shifts():
            async with db_manager.get_session() as session:
                time_slot_service = TimeSlotService()
                
                # Автоматически закрываем просроченные смены
                result = await time_slot_service.auto_close_expired_shifts()
                
                if result.get('success'):
                    closed_count = result.get('closed_count', 0)
                    errors = result.get('errors', [])
                    
                    logger.info(
                        "Auto-close shifts completed",
                        closed_count=closed_count,
                        errors_count=len(errors)
                    )
                    
                    if errors:
                        for error in errors:
                            logger.error(f"Auto-close error: {error}")
                    
                    return closed_count
                else:
                    logger.error(f"Auto-close shifts failed: {result.get('error')}")
                    return 0
        
        import asyncio
        closed_count = asyncio.run(_auto_close_shifts())
        
        logger.info(f"Auto-closed {closed_count} shifts")
        return closed_count
        
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
