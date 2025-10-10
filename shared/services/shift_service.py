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
from sqlalchemy import select, and_
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
                await session.commit()
                await session.refresh(new_shift)
                
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
                active_shift.end_time = datetime.now()
                active_shift.status = "completed"
                
                # Рассчитываем время и оплату
                duration = active_shift.end_time - active_shift.start_time
                hours = duration.total_seconds() / 3600
                active_shift.total_hours = hours
                active_shift.total_payment = hours * active_shift.hourly_rate
                
                # Создаем корректировки начислений (Phase 4A)
                from shared.services.payroll_adjustment_service import PayrollAdjustmentService
                from shared.services.late_penalty_calculator import LatePenaltyCalculator
                
                adjustment_service = PayrollAdjustmentService(session)
                late_penalty_calc = LatePenaltyCalculator(session)
                
                # 1. Создать базовую оплату за смену
                await adjustment_service.create_shift_base_adjustment(
                    shift=active_shift,
                    employee_id=user.id,
                    object_id=active_shift.object_id,
                    created_by=user.id
                )
                
                # 2. Проверить и создать штраф за опоздание
                late_minutes, penalty_amount = await late_penalty_calc.calculate_late_penalty(
                    shift=active_shift,
                    obj=active_shift.object
                )
                
                if penalty_amount > 0:
                    await adjustment_service.create_late_start_adjustment(
                        shift=active_shift,
                        late_minutes=late_minutes,
                        penalty_amount=penalty_amount,
                        created_by=user.id
                    )
                
                # 3. Обработать задачи смены (из shift.object.shift_tasks JSONB)
                # TODO: Реализовать после доработки модели задач
                
                await session.commit()
                
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












