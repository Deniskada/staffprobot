"""Планировщик для автоматического закрытия смен."""

import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
from core.database.session import get_async_session
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from shared.services.shift_history_service import ShiftHistoryService
from shared.services.shift_notification_service import ShiftNotificationService
from shared.services.shift_status_sync_service import ShiftStatusSyncService
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession


class ShiftScheduler:
    """Планировщик для автоматического управления сменами."""
    
    def __init__(self):
        """Инициализация планировщика."""
        self.is_running = False
        self.check_interval = 300  # 5 минут
        
        logger.info("ShiftScheduler initialized")
    
    async def start(self):
        """Запуск планировщика."""
        if self.is_running:
            logger.warning("ShiftScheduler is already running")
            return
        
        self.is_running = True
        logger.info("ShiftScheduler started")
        
        try:
            while self.is_running:
                await self._check_and_close_shifts()
                await asyncio.sleep(self.check_interval)
        except Exception as e:
            logger.error("ShiftScheduler error: " + str(e))
            self.is_running = False
            raise
    
    async def stop(self):
        """Остановка планировщика."""
        self.is_running = False
        logger.info("ShiftScheduler stopped")
    
    async def _check_and_close_shifts(self):
        """Проверяет и закрывает смены, которые должны быть закрыты."""
        try:
            async with get_async_session() as session:
                # Получаем активные смены
                active_shifts = await self._get_active_shifts(session)
                
                if not active_shifts:
                    logger.debug("No active shifts to check")
                    return
                
                logger.info("Checking " + str(len(active_shifts)) + " active shifts")
                
                closed_shifts: List[tuple[int, float, Optional[float], datetime]] = []
                # Проверяем каждую смену
                for shift in active_shifts:
                    result = await self._check_shift_closure(session, shift)
                    if result:
                        closed_shifts.append(result)
                
                await session.commit()

            for shift_id, total_hours, total_payment, finished_at in closed_shifts:
                try:
                    await ShiftNotificationService().notify_shift_completed(
                        shift_id=shift_id,
                        actor_role="system",
                        total_hours=total_hours,
                        total_payment=total_payment,
                        auto=True,
                        finished_at=finished_at,
                    )
                except Exception as notification_error:
                    logger.warning(
                        "Failed to send auto-close notification",
                        shift_id=shift_id,
                        error=str(notification_error),
                    )
                
        except Exception as e:
            logger.error("Error in shift check cycle: " + str(e))
    
    async def _get_active_shifts(self, session: AsyncSession) -> List[Shift]:
        """Получает все активные смены."""
        try:
            query = select(Shift).where(
                and_(
                    Shift.status == 'active',
                    Shift.end_time.is_(None)
                )
            )
            result = await session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Error getting active shifts: " + str(e))
            return []
    
    async def _check_shift_closure(self, session: AsyncSession, shift: Shift):
        """Проверяет, нужно ли закрыть смену."""
        try:
            # Получаем объект для проверки времени работы
            object_query = select(shift.object.__class__).where(
                shift.object.__class__.id == shift.object_id
            )
            object_result = await session.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            if not obj:
                logger.warning("Object " + str(shift.object_id) + " not found for shift " + str(shift.id))
                return
            
            # Проверяем, нужно ли закрыть смену
            should_close = await self._should_close_shift(shift, obj)
            
            if should_close:
                return await self._auto_close_shift(session, shift)

            return None
                
        except Exception as e:
            logger.error("Error checking shift " + str(shift.id) + ": " + str(e))
            return None
    
    async def _should_close_shift(self, shift: Shift, obj) -> bool:
        """
        Определяет, нужно ли автоматически закрыть смену.
        
        Args:
            shift: Смена для проверки
            obj: Объект смены
            
        Returns:
            True, если смену нужно закрыть
        """
        try:
            now = datetime.now()
            shift_start = shift.start_time
            
            # Проверяем, прошло ли 24 часа с начала смены
            if now - shift_start > timedelta(days=1):
                logger.info(
                    "Shift " + str(shift.id) + " should be closed: more than 24 hours passed"
                )
                return True
            
            # Проверяем, работает ли объект сейчас
            if hasattr(obj, 'opening_time') and hasattr(obj, 'closing_time'):
                current_time = now.time()
                
                # Если объект закрыт и прошло время после закрытия
                if current_time > obj.closing_time:
                    # Закрываем смену через 1 час после закрытия объекта
                    closing_deadline = datetime.combine(now.date(), obj.closing_time) + timedelta(hours=1)
                    
                    if now > closing_deadline:
                        logger.info(
                            "Shift " + str(shift.id) + " should be closed: object is closed"
                        )
                        return True
            
            return False
            
        except Exception as e:
            logger.error("Error determining if shift should be closed: " + str(e))
            return False
    
    async def _auto_close_shift(self, session: AsyncSession, shift: Shift) -> Optional[tuple[int, float, Optional[float], datetime]]:
        """Автоматически закрывает смену."""
        try:
            now = datetime.now(timezone.utc)
            
            # Вычисляем общее время работы
            duration = now - shift.start_time
            total_hours = round(duration.total_seconds() / 3600, 2)
            
            # Вычисляем оплату
            hourly_rate = float(shift.hourly_rate) if shift.hourly_rate else 0.0
            total_payment = round(total_hours * hourly_rate, 2) if hourly_rate > 0 else None
            
            # Обновляем смену
            previous_status = shift.status
            update_query = update(Shift).where(Shift.id == shift.id).values(
                end_time=now,
                status='completed',  # Используем стандартный статус completed вместо auto_closed
                total_hours=total_hours,
                total_payment=total_payment,
                notes="Автоматически закрыта в " + now.strftime('%H:%M:%S')
            )
            
            await session.execute(update_query)
            
            # Обновляем объект shift для синхронизации
            shift.status = "completed"
            shift.end_time = now
            shift.total_hours = total_hours
            shift.total_payment = total_payment

            # Синхронизация статусов при закрытии смены
            sync_service = ShiftStatusSyncService(session)
            if shift.schedule_id:
                await sync_service.sync_on_shift_close(
                    shift,
                    actor_id=None,
                    actor_role="system",
                    source="celery",
                    payload={
                        "auto_closed_at": now.isoformat(),
                        "total_hours": total_hours,
                        "total_payment": total_payment,
                    },
                )

            history_service = ShiftHistoryService(session)
            await history_service.log_event(
                operation="shift_close",
                source="celery",
                actor_id=None,
                actor_role="system",
                shift_id=shift.id,
                schedule_id=getattr(shift, "schedule_id", None),
                old_status=previous_status,
                new_status="completed",
                payload={
                    "auto_closed_at": now.isoformat(),
                    "total_hours": total_hours,
                    "total_payment": total_payment,
                },
            )

            logger.info(
                "Shift " + str(shift.id) + " auto-closed"
            )

            return (shift.id, total_hours, total_payment, now)
            
        except Exception as e:
            logger.error("Error auto-closing shift " + str(shift.id) + ": " + str(e))
            return None
    
    async def close_shift_manually(
        self, 
        shift_id: int, 
        end_time: Optional[datetime] = None,
        end_coordinates: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Ручное закрытие смены.
        
        Args:
            shift_id: ID смены
            end_time: Время окончания (по умолчанию - сейчас)
            end_coordinates: Координаты окончания
            notes: Заметки
            
        Returns:
            True, если смена успешно закрыта
        """
        try:
            async with get_async_session() as session:
                # Получаем смену
                shift_query = select(Shift).where(Shift.id == shift_id)
                shift_result = await session.execute(shift_query)
                shift = shift_result.scalar_one_or_none()
                
                if not shift:
                    logger.error("Shift " + str(shift_id) + " not found")
                    return False
                
                if shift.status != 'active':
                    logger.warning("Shift " + str(shift_id) + " is not active (status: " + shift.status + ")")
                    return False
                
                # Устанавливаем время окончания
                close_time = end_time or datetime.now(timezone.utc)
                
                # Вычисляем общее время и оплату
                duration = close_time - shift.start_time
                total_hours = round(duration.total_seconds() / 3600, 2)
                
                hourly_rate = float(shift.hourly_rate) if shift.hourly_rate else 0.0
                total_payment = round(total_hours * hourly_rate, 2) if hourly_rate > 0 else None
                
                # Обновляем смену
                update_data = {
                    'end_time': close_time,
                    'status': 'completed',
                    'total_hours': total_hours,
                    'total_payment': total_payment
                }
                
                if end_coordinates:
                    update_data['end_coordinates'] = end_coordinates
                
                if notes:
                    update_data['notes'] = notes
                
                update_query = update(Shift).where(Shift.id == shift_id).values(**update_data)
                await session.execute(update_query)
                
                # Обновляем объект shift для синхронизации
                previous_status = shift.status
                shift.status = update_data.get('status', 'completed')
                shift.end_time = close_time
                shift.total_hours = total_hours
                shift.total_payment = total_payment
                if end_coordinates:
                    shift.end_coordinates = end_coordinates
                if notes:
                    shift.notes = notes

                # Синхронизация статусов при закрытии смены
                sync_service = ShiftStatusSyncService(session)
                if shift.schedule_id:
                    await sync_service.sync_on_shift_close(
                        shift,
                        actor_id=None,
                        actor_role="system",
                        source="web",
                        payload={
                            "end_coordinates": end_coordinates,
                            "notes": notes,
                            "manual": True,
                        },
                    )

                history_service = ShiftHistoryService(session)
                await history_service.log_event(
                    operation="shift_close",
                    source="web",
                    actor_id=None,
                    actor_role="system",
                    shift_id=shift_id,
                    schedule_id=shift.schedule_id,
                    old_status=previous_status,
                    new_status=update_data.get('status', 'completed'),
                    payload={
                        "end_coordinates": end_coordinates,
                        "notes": notes,
                        "manual": True,
                    },
                )

                await session.commit()
                
                logger.info(
                    "Shift " + str(shift_id) + " manually closed"
                )

                try:
                    await ShiftNotificationService().notify_shift_completed(
                        shift_id=shift_id,
                        actor_role="system",
                        total_hours=total_hours,
                        total_payment=total_payment,
                        auto=False,
                        finished_at=close_time,
                    )
                except Exception as notification_error:
                    logger.warning(
                        "Failed to send manual close notification",
                        shift_id=shift_id,
                        error=str(notification_error),
                    )
                
                # Инвалидация кэша календаря
                from core.cache.redis_cache import cache
                await cache.clear_pattern("calendar_shifts:*")
                await cache.clear_pattern("api_response:*")  # API responses
                
                return True
                
        except Exception as e:
            logger.error("Error manually closing shift " + str(shift_id) + ": " + str(e))
            return False
    
    async def get_shift_status(self, shift_id: int) -> Optional[dict]:
        """
        Получает статус смены.
        
        Args:
            shift_id: ID смены
            
        Returns:
            Словарь со статусом смены или None
        """
        try:
            async with get_async_session() as session:
                shift_query = select(Shift).where(Shift.id == shift_id)
                shift_result = await session.execute(shift_query)
                shift = shift_result.scalar_one_or_none()
                
                if not shift:
                    return None
                
                return {
                    'id': shift.id,
                    'user_id': shift.user_id,
                    'object_id': shift.object_id,
                    'status': shift.status,
                    'start_time': shift.start_time,
                    'end_time': shift.end_time,
                    'total_hours': shift.total_hours,
                    'total_payment': shift.total_payment,
                    'is_active': shift.status == 'active'
                }
                
        except Exception as e:
            logger.error("Error getting shift status " + str(shift_id) + ": " + str(e))
            return None
