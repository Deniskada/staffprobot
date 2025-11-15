"""Общий сервис для работы со сменами."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from core.logging.logger import logger
from core.geolocation.location_validator import LocationValidator
from core.scheduler.shift_scheduler import ShiftScheduler
from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.user import User
from shared.services.shift_history_service import ShiftHistoryService
from shared.services.shift_notification_service import ShiftNotificationService
from shared.services.shift_status_sync_service import ShiftStatusSyncService
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from .base_service import BaseService


class ShiftService(BaseService):
    """Общий сервис для работы со сменами."""
    
    def _initialize_service(self):
        """Инициализация сервиса."""
        self.location_validator = LocationValidator()
        self.scheduler = ShiftScheduler()
        logger.info("Shared ShiftService initialized with geolocation support")
    
    async def open_shift(
        self, 
        user_id: int, 
        object_id: int, 
        coordinates: str
    ) -> Dict[str, Any]:
        """
        Открывает новую смену для пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            object_id: ID объекта
            coordinates: Координаты в формате "lat,lng"
            
        Returns:
            Результат открытия смены
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
                
                # Получаем объект
                object_query = select(Object).where(Object.id == object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }
                
                # Проверяем, нет ли уже активной смены
                active_shift_query = select(Shift).where(
                    and_(
                        Shift.user_id == user.id,
                        Shift.status == "active"
                    )
                )
                active_shift_result = await session.execute(active_shift_query)
                active_shift = active_shift_result.scalar_one_or_none()
                
                if active_shift:
                    return {
                        'success': False,
                        'error': 'У вас уже есть активная смена'
                    }
                
                # Проверяем геолокацию
                lat, lng = map(float, coordinates.split(','))
                is_valid, distance = self.location_validator.validate_location(
                    lat, lng, obj.latitude, obj.longitude
                )
                
                if not is_valid:
                    return {
                        'success': False,
                        'error': f'Вы находитесь слишком далеко от объекта (расстояние: {distance:.0f}м)'
                    }
                
                # Создаем новую смену
                new_shift = Shift(
                    user_id=user.id,
                    object_id=object_id,
                    start_time=datetime.now(),
                    hourly_rate=obj.hourly_rate,
                    status="active"
                )
                
                session.add(new_shift)
                await session.flush()

                # Синхронизация статусов при открытии смены из расписания
                sync_service = ShiftStatusSyncService(session)
                if new_shift.schedule_id:
                    await sync_service.sync_on_shift_open(
                        new_shift,
                        actor_id=user.id,
                        actor_role="employee",
                        source="bot",
                        payload={
                            "object_id": object_id,
                            "coordinates": coordinates,
                        },
                    )

                history_service = ShiftHistoryService(session)
                await history_service.log_event(
                    operation="shift_open",
                    source="bot",
                    actor_id=user.id,
                    actor_role="employee",
                    shift_id=new_shift.id,
                    schedule_id=new_shift.schedule_id,
                    old_status=None,
                    new_status="active",
                    payload={
                        "object_id": object_id,
                        "coordinates": coordinates,
                    },
                )

                await session.commit()
                await session.refresh(new_shift)

                try:
                    await ShiftNotificationService().notify_shift_started(
                        shift_id=new_shift.id,
                        actor_role="employee",
                    )
                except Exception as notification_error:
                    logger.warning(
                        "Failed to send shift started notification",
                        shift_id=new_shift.id,
                        error=str(notification_error),
                    )
                
                logger.info(
                    f"Shift opened successfully",
                    user_id=user_id,
                    shift_id=new_shift.id,
                    object_id=object_id,
                    coordinates=coordinates
                )
                
                return {
                    'success': True,
                    'shift_id': new_shift.id,
                    'message': f'Смена открыта на объекте "{obj.name}"'
                }
                
        except Exception as e:
            logger.error(f"Error opening shift: {e}")
            return {
                'success': False,
                'error': f'Ошибка открытия смены: {str(e)}'
            }
    
    async def close_shift(
        self, 
        user_id: int, 
        coordinates: str
    ) -> Dict[str, Any]:
        """
        Закрывает активную смену пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            coordinates: Координаты в формате "lat,lng"
            
        Returns:
            Результат закрытия смены
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
                
                # Получаем активную смену
                active_shift_query = select(Shift).options(
                    joinedload(Shift.object)
                ).where(
                    and_(
                        Shift.user_id == user.id,
                        Shift.status == "active"
                    )
                )
                active_shift_result = await session.execute(active_shift_query)
                active_shift = active_shift_result.scalar_one_or_none()
                
                if not active_shift:
                    return {
                        'success': False,
                        'error': 'У вас нет активных смен'
                    }
                
                # Проверяем геолокацию
                lat, lng = map(float, coordinates.split(','))
                is_valid, distance = self.location_validator.validate_location(
                    lat, lng, active_shift.object.latitude, active_shift.object.longitude
                )
                
                if not is_valid:
                    return {
                        'success': False,
                        'error': f'Вы находитесь слишком далеко от объекта (расстояние: {distance:.0f}м)'
                    }
                
                # Закрываем смену
                previous_shift_status = active_shift.status
                active_shift.end_time = datetime.now()
                active_shift.status = "completed"
                
                # Рассчитываем время и оплату
                duration = active_shift.end_time - active_shift.start_time
                hours = duration.total_seconds() / 3600
                active_shift.total_hours = hours
                active_shift.total_payment = hours * active_shift.hourly_rate
                
                # Синхронизация статусов при закрытии смены
                sync_service = ShiftStatusSyncService(session)
                if active_shift.schedule_id:
                    await sync_service.sync_on_shift_close(
                        active_shift,
                        actor_id=user.id,
                        actor_role="employee",
                        source="bot",
                        payload={
                            "object_id": active_shift.object_id,
                            "coordinates": coordinates,
                            "hours": hours,
                            "payment": float(active_shift.total_payment) if active_shift.total_payment else None,
                        },
                    )
                
                history_service = ShiftHistoryService(session)
                await history_service.log_event(
                    operation="shift_close",
                    source="bot",
                    actor_id=user.id,
                    actor_role="employee",
                    shift_id=active_shift.id,
                    schedule_id=active_shift.schedule_id,
                    old_status=previous_shift_status,
                    new_status=active_shift.status,
                    payload={
                        "object_id": active_shift.object_id,
                        "coordinates": coordinates,
                        "hours": hours,
                        "payment": float(active_shift.total_payment) if active_shift.total_payment else None,
                    },
                )

                await session.commit()

                try:
                    await ShiftNotificationService().notify_shift_completed(
                        shift_id=active_shift.id,
                        actor_role="employee",
                        total_hours=hours,
                        total_payment=float(active_shift.total_payment) if active_shift.total_payment else None,
                        auto=False,
                        finished_at=active_shift.end_time,
                    )
                except Exception as notification_error:
                    logger.warning(
                        "Failed to send shift completed notification",
                        shift_id=active_shift.id,
                        error=str(notification_error),
                    )
                
                logger.info(
                    f"Shift closed successfully",
                    user_id=user_id,
                    shift_id=active_shift.id,
                    hours=hours,
                    payment=active_shift.total_payment
                )
                
                return {
                    'success': True,
                    'shift_id': active_shift.id,
                    'object_id': active_shift.object_id,
                    'hours': hours,
                    'payment': active_shift.total_payment,
                    'message': f'Смена закрыта. Время: {hours:.1f}ч, Оплата: {active_shift.total_payment:.0f}₽'
                }
                
        except Exception as e:
            logger.error(f"Error closing shift: {e}")
            return {
                'success': False,
                'error': f'Ошибка закрытия смены: {str(e)}'
            }
    
    async def get_user_active_shifts(
        self, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получает активные смены пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Список активных смен
        """
        try:
            async with get_async_session() as session:
                # Получаем пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return []
                
                # Получаем активные смены
                active_shifts_query = select(Shift).options(
                    joinedload(Shift.object)
                ).where(
                    and_(
                        Shift.user_id == user.id,
                        Shift.status == "active"
                    )
                )
                active_shifts_result = await session.execute(active_shifts_query)
                active_shifts = active_shifts_result.scalars().all()
                
                # Формируем список смен
                shifts_list = []
                for shift in active_shifts:
                    shifts_list.append({
                        'id': shift.id,
                        'object_id': shift.object_id,
                        'object_name': shift.object.name,
                        'start_time': shift.start_time,
                        'hourly_rate': shift.hourly_rate,
                        'status': shift.status
                    })
                
                return shifts_list
                
        except Exception as e:
            logger.error(f"Error getting user active shifts: {e}")
            return []
    
    async def get_user_shift_history(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получает историю смен пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            limit: Максимальное количество смен
            
        Returns:
            Список смен
        """
        try:
            async with get_async_session() as session:
                # Получаем пользователя
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return []
                
                # Получаем смены
                shifts_query = select(Shift).options(
                    joinedload(Shift.object)
                ).where(
                    Shift.user_id == user.id
                ).order_by(Shift.start_time.desc()).limit(limit)
                
                shifts_result = await session.execute(shifts_query)
                shifts = shifts_result.scalars().all()
                
                # Формируем список смен
                shifts_list = []
                for shift in shifts:
                    shifts_list.append({
                        'id': shift.id,
                        'object_name': shift.object.name,
                        'start_time': shift.start_time,
                        'end_time': shift.end_time,
                        'total_hours': shift.total_hours,
                        'total_payment': shift.total_payment,
                        'status': shift.status
                    })
                
                return shifts_list
                
        except Exception as e:
            logger.error(f"Error getting user shift history: {e}")
            return []












