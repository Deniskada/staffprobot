"""Сервис для работы со сменами."""

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


class ShiftService:
    """Сервис для работы со сменами."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.location_validator = LocationValidator()
        self.scheduler = ShiftScheduler()
        
        logger.info("ShiftService initialized with geolocation support")
    
    async def open_shift(
        self, 
        user_id: int, 
        object_id: int, 
        coordinates: str, 
        shift_type: str = "spontaneous",
        timeslot_id: Optional[int] = None,
        schedule_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Открытие смены с проверкой геолокации.
        
        Args:
            user_id: ID пользователя
            object_id: ID объекта
            coordinates: Координаты пользователя в формате 'lat,lon'
            
        Returns:
            Словарь с результатом операции
        """
        try:
            logger.info(
                f"Opening shift requested: user_id={user_id}, object_id={object_id}, coordinates={coordinates}"
            )
            
            async with get_async_session() as session:
                # Проверяем существование пользователя
                # ОТКЛЮЧЕНО для тестирования с JSON файлом
                # user = await self._get_user(session, user_id)
                # if not user:
                #     return {
                #         'success': False,
                #         'error': 'Пользователь не найден'
                #     }
                
                # Проверяем существование объекта
                obj = await self._get_object(session, object_id)
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }
                
                # Загружаем TimeSlot заранее (если есть), чтобы избежать greenlet ошибок
                timeslot_obj = None
                if timeslot_id:
                    from domain.entities.time_slot import TimeSlot
                    timeslot_query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
                    timeslot_result = await session.execute(timeslot_query)
                    timeslot_obj = timeslot_result.scalar_one_or_none()
                
                # Находим пользователя по telegram_id для получения его id в БД
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден в базе данных. Обратитесь к администратору.'
                    }
                
                # Проверяем, нет ли уже активной смены у пользователя
                active_shift = await self._get_active_shift(session, db_user.id)
                if active_shift:
                    return {
                        'success': False,
                        'error': 'У вас уже есть активная смена'
                    }
                
                # Валидируем геолокацию с использованием max_distance_meters из объекта
                location_validation = self.location_validator.validate_shift_location(
                    coordinates, obj.coordinates, obj.max_distance_meters
                )
                
                if not location_validation['valid']:
                    return {
                        'success': False,
                        'error': location_validation['error'],
                        'distance_meters': location_validation.get('distance_meters'),
                        'max_distance_meters': location_validation.get('max_distance_meters')
                    }
                
                # Автоматически открываем объект (если еще не открыт)
                from shared.services.object_opening_service import ObjectOpeningService
                opening_service = ObjectOpeningService(session)
                
                is_open = await opening_service.is_object_open(object_id)
                if not is_open:
                    try:
                        await opening_service.open_object(
                            object_id=object_id,
                            user_id=db_user.id,
                            coordinates=coordinates
                        )
                        logger.info(
                            f"Object auto-opened before shift opening",
                            object_id=object_id,
                            user_id=user_id
                        )
                    except ValueError as e:
                        logger.warning(f"Failed to auto-open object: {e}")
                        # Продолжаем открытие смены даже если объект не открылся
                
                # Определяем ставку с учетом приоритета договора
                timeslot_rate = None
                rate_source = "object"
                
                # Если это запланированная смена, получаем ставку из расписания/тайм-слота
                logger.info(f"Shift type: {shift_type}, schedule_id: {schedule_id}, timeslot_id: {timeslot_id}")
                if shift_type == "planned" and schedule_id:
                    from apps.bot.services.shift_schedule_service import ShiftScheduleService
                    schedule_service = ShiftScheduleService()
                    schedule_data = await schedule_service.get_shift_schedule_by_id(schedule_id)
                    
                    if schedule_data:
                        logger.info(f"Schedule data: {schedule_data}")
                        schedule_rate = schedule_data.get('hourly_rate')
                        if schedule_rate:
                            timeslot_rate = schedule_rate
                            rate_source = "schedule"
                            logger.info(f"Found schedule rate: {schedule_rate}")
                    else:
                        logger.warning(f"No schedule data found for schedule_id: {schedule_id}")
                else:
                    # Для спонтанной смены проверяем доступные тайм-слоты на сегодня
                    if shift_type == "spontaneous":
                        from apps.bot.services.timeslot_service import TimeSlotService
                        from datetime import date
                        
                        timeslot_service = TimeSlotService()
                        today = date.today()
                        available_timeslots = await timeslot_service.get_available_timeslots_for_object(object_id, today)
                        
                        if available_timeslots:
                            # Есть доступные тайм-слоты - берем ставку из первого
                            first_timeslot = available_timeslots[0]
                            if first_timeslot.get('hourly_rate'):
                                timeslot_rate = first_timeslot.get('hourly_rate')
                                rate_source = "timeslot"
                                logger.info(f"Found timeslot rate for spontaneous shift: {timeslot_rate}")
                
                # Получаем активный договор сотрудника для КОНКРЕТНОГО объекта
                from domain.entities.contract import Contract
                from sqlalchemy import or_, cast, func
                from sqlalchemy.dialects.postgresql import JSONB
                from shared.services.contract_validation_service import build_active_contract_filter
                from datetime import date
                
                # Ищем договор для этого объекта (allowed_objects содержит object_id)
                # Cast allowed_objects к JSONB для использования оператора @>
                contract_query = select(Contract).where(
                    and_(
                        Contract.employee_id == db_user.id,
                        build_active_contract_filter(date.today()),
                        cast(Contract.allowed_objects, JSONB).op('@>')(cast([object_id], JSONB))
                    )
                ).order_by(Contract.use_contract_rate.desc())  # Приоритет договорам с use_contract_rate=True
                
                contract_result = await session.execute(contract_query)
                active_contract = contract_result.scalars().first()
                
                # Логирование цепочки принятия решений по ставке
                logger.info(
                    "Rate calculation chain started",
                    object_id=object_id,
                    object_rate=float(obj.hourly_rate),
                    timeslot_rate=timeslot_rate,
                    has_contract=active_contract is not None,
                    contract_rate=float(active_contract.hourly_rate) if active_contract and active_contract.hourly_rate else None,
                    use_contract_rate=active_contract.use_contract_rate if active_contract else None,
                    payment_system_id=active_contract.payment_system_id if active_contract else None,
                    org_unit_id=obj.org_unit_id if hasattr(obj, 'org_unit_id') else None
                )
                
                # Определяем финальную ставку с учетом приоритетов
                if active_contract:
                    hourly_rate = active_contract.get_effective_hourly_rate(
                        timeslot_rate=timeslot_rate,
                        object_rate=float(obj.hourly_rate)
                    )
                    
                    if active_contract.use_contract_rate and active_contract.hourly_rate:
                        rate_source = "contract"
                        logger.info(
                            "Final rate decision: contract (highest priority)",
                            hourly_rate=hourly_rate,
                            contract_id=active_contract.id,
                            payment_system_id=active_contract.payment_system_id
                        )
                    elif timeslot_rate:
                        rate_source = "timeslot"
                        logger.info(
                            "Final rate decision: timeslot",
                            hourly_rate=hourly_rate,
                            timeslot_id=timeslot_id
                        )
                    else:
                        rate_source = "object"
                        logger.info(
                            "Final rate decision: object",
                            hourly_rate=hourly_rate,
                            object_id=object_id,
                            org_unit_id=obj.org_unit_id if hasattr(obj, 'org_unit_id') else None
                        )
                else:
                    # Нет активного договора - используем timeslot или object
                    hourly_rate = timeslot_rate if timeslot_rate else float(obj.hourly_rate)
                    rate_source = "timeslot" if timeslot_rate else "object"
                    logger.info(
                        "Final rate decision: no contract",
                        hourly_rate=hourly_rate,
                        rate_source=rate_source
                    )
                
                # Вычисляем planned_start и actual_start для штрафов за опоздание
                from datetime import date as date_class, time as time_class
                from domain.entities.time_slot import TimeSlot
                
                current_time = datetime.now()
                planned_start = None
                
                # Получить late_threshold_minutes из объекта или org_unit
                late_threshold_minutes = 0
                if not obj.inherit_late_settings and obj.late_threshold_minutes is not None:
                    late_threshold_minutes = obj.late_threshold_minutes
                elif obj.org_unit:
                    org_unit = obj.org_unit
                    while org_unit:
                        if not org_unit.inherit_late_settings and org_unit.late_threshold_minutes is not None:
                            late_threshold_minutes = org_unit.late_threshold_minutes
                            break
                        org_unit = org_unit.parent
                
                # Вычисляем planned_start только для ЗАПЛАНИРОВАННЫХ смен
                planned_start = None
                
                if shift_type == "planned" and timeslot_obj:
                    # Запланированная смена: planned_start = timeslot.start_time + threshold
                    import pytz
                    from datetime import datetime as dt, timedelta
                    
                    object_timezone = obj.timezone or 'Europe/Moscow'
                    object_tz = pytz.timezone(object_timezone)
                    
                    # Получить late_threshold_minutes из объекта или org_unit
                    late_threshold_minutes = 0
                    if not obj.inherit_late_settings and obj.late_threshold_minutes is not None:
                        late_threshold_minutes = obj.late_threshold_minutes
                    elif obj.org_unit:
                        org_unit = obj.org_unit
                        while org_unit:
                            if not org_unit.inherit_late_settings and org_unit.late_threshold_minutes is not None:
                                late_threshold_minutes = org_unit.late_threshold_minutes
                                break
                            org_unit = org_unit.parent
                    
                    # timeslot.start_time уже в локальном времени объекта
                    base_time = dt.combine(timeslot_obj.slot_date, timeslot_obj.start_time)
                    # Локализуем naive datetime в timezone объекта
                    base_time = object_tz.localize(base_time)
                    planned_start = base_time + timedelta(minutes=late_threshold_minutes)
                # Для спонтанных смен planned_start = NULL (нет опозданий)
                
                # Создаем новую смену
                new_shift = Shift(
                    user_id=db_user.id,  # Используем id из БД, а не telegram_id
                    object_id=object_id,
                    start_time=current_time,
                    actual_start=current_time,  # Фактическое время начала работы
                    planned_start=planned_start,  # Плановое время (для штрафов)
                    status='active',
                    start_coordinates=coordinates,
                    hourly_rate=hourly_rate,
                    time_slot_id=timeslot_id if shift_type == "planned" else None,
                    schedule_id=schedule_id if shift_type == "planned" else None,
                    is_planned=shift_type == "planned"
                )
                
                session.add(new_shift)
                await session.flush()  # Получаем new_shift.id без коммита
                
                # Синхронизация статусов при открытии смены из расписания
                if shift_type == "planned" and schedule_id:
                    from shared.services.shift_status_sync_service import ShiftStatusSyncService
                    sync_service = ShiftStatusSyncService(session)
                    await sync_service.sync_on_shift_open(
                        new_shift,
                        actor_id=db_user.id,
                        actor_role="employee",
                        source="bot",
                        payload={
                            "object_id": object_id,
                            "coordinates": coordinates,
                        },
                    )
                
                # Tasks v2: Создаём TaskEntryV2 для только что открытой смены (ДО коммита, в той же транзакции)
                try:
                    from core.celery.tasks.task_assignment import create_task_entries_for_shift
                    created_entries = await create_task_entries_for_shift(session, new_shift)
                    logger.info(f"Created {created_entries} TaskEntryV2 for shift {new_shift.id}")
                except Exception as e:
                    logger.error(f"Failed to create TaskEntryV2 for shift {new_shift.id}: {e}")
                    # Не блокируем успешное открытие смены
                
                await session.commit()
                await session.refresh(new_shift)
                
                logger.info(
                    f"Shift opened successfully: shift_id={new_shift.id}, user_id={user_id}, object_id={object_id}, coordinates={coordinates}, distance_meters={location_validation['distance_meters']}"
                )
                
                # Инвалидация кэша календаря
                from core.cache.redis_cache import cache
                await cache.clear_pattern("calendar_shifts:*")
                await cache.clear_pattern("api_response:*")  # API responses
                
                # Форматируем время в часовом поясе объекта
                object_timezone = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                local_start_time = timezone_helper.format_local_time(new_shift.start_time, object_timezone)
                
                return {
                    'success': True,
                    'shift_id': new_shift.id,
                    'message': f'Смена успешно открыта! {location_validation["message"]}',
                    'start_time': local_start_time,
                    'object_name': obj.name,
                    'hourly_rate': float(new_shift.hourly_rate)
                }
                
        except Exception as e:
            logger.error(
                f"Error opening shift: user_id={user_id}, object_id={object_id}, coordinates={coordinates}, error={str(e)}"
            )
            return {
                'success': False,
                'error': f'Ошибка при открытии смены: {str(e)}'
            }
    
    async def close_shift(
        self, 
        user_id: int, 
        shift_id: int, 
        coordinates: str
    ) -> Dict[str, Any]:
        """
        Закрытие смены с проверкой геолокации.
        
        Args:
            user_id: ID пользователя
            shift_id: ID смены
            coordinates: Координаты пользователя в формате 'lat,lon'
            
        Returns:
            Словарь с результатом операции
        """
        try:
            logger.info(
                f"Closing shift requested: user_id={user_id}, shift_id={shift_id}, coordinates={coordinates}"
            )
            
            async with get_async_session() as session:
                # Находим пользователя по telegram_id для получения его id в БД
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден в базе данных. Обратитесь к администратору.'
                    }
                
                # Получаем смену
                shift = await self._get_shift(session, shift_id)
                if not shift:
                    return {
                        'success': False,
                        'error': 'Смена не найдена'
                    }
                
                # Проверяем, принадлежит ли смена пользователю
                if shift.user_id != db_user.id:
                    return {
                        'success': False,
                        'error': 'Смена не принадлежит вам'
                    }
                
                # Проверяем, активна ли смена
                if shift.status != 'active':
                    return {
                        'success': False,
                        'error': f'Смена уже {shift.status}'
                    }
                
                # Получаем объект для проверки геолокации
                obj = await self._get_object(session, shift.object_id)
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект смены не найден'
                    }
                
                # Валидируем геолокацию при закрытии с использованием max_distance_meters из объекта
                location_validation = self.location_validator.validate_shift_location(
                    coordinates, obj.coordinates, obj.max_distance_meters
                )
                
                if not location_validation['valid']:
                    return {
                        'success': False,
                        'error': location_validation['error'],
                        'distance_meters': location_validation.get('distance_meters'),
                        'max_distance_meters': location_validation.get('max_distance_meters')
                    }
                
                # Закрываем смену
                success = await self.scheduler.close_shift_manually(
                    shift_id=shift_id,
                    end_coordinates=coordinates,
                    notes=f"Закрыта пользователем в {datetime.now().strftime('%H:%M:%S')}"
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': 'Ошибка при закрытии смены'
                    }
                
                # Синхронизация статусов выполняется в scheduler.close_shift_manually
                # Дополнительная синхронизация не требуется
                
                # Получаем обновленную информацию о смене в новой сессии (после коммита close_shift_manually)
                async with get_async_session() as fresh_session:
                    updated_shift = await self._get_shift(fresh_session, shift_id)
                    
                    if not updated_shift:
                        logger.error(f"Could not retrieve updated shift {shift_id} after closing")
                        return {
                            'success': True,  # Смена закрыта, но не можем получить детали
                            'message': f'Смена успешно закрыта! {location_validation["message"]}',
                            'shift_id': shift_id,
                            'total_hours': 0,
                            'total_payment': 0,
                            'end_time': None
                        }
                    
                    logger.info(
                        f"Shift closed successfully: shift_id={shift_id}, user_id={user_id}, object_id={shift.object_id}, coordinates={coordinates}, total_hours={updated_shift.total_hours}, total_payment={updated_shift.total_payment}"
                    )
                    
                    # Phase 4A: Корректировки создаются через Celery задачу
                    
                    # Форматируем время в часовом поясе объекта
                    object_timezone = getattr(shift.object, 'timezone', None) or 'Europe/Moscow'
                    local_end_time = timezone_helper.format_local_time(updated_shift.end_time, object_timezone) if updated_shift.end_time else None
                    
                    return {
                        'success': True,
                        'message': f'Смена успешно закрыта! {location_validation["message"]}',
                        'shift_id': shift_id,
                        'object_id': shift.object_id,
                        'total_hours': float(updated_shift.total_hours) if updated_shift.total_hours else 0,
                        'total_payment': float(updated_shift.total_payment) if updated_shift.total_payment else 0,
                        'end_time': local_end_time
                    }
                
        except Exception as e:
            logger.error(
                f"Error closing shift: user_id={user_id}, shift_id={shift_id}, coordinates={coordinates}, error={str(e)}"
            )
            return {
                'success': False,
                'error': f'Ошибка при закрытии смены: {str(e)}'
            }
    
    async def get_user_shifts(
        self, 
        user_id: int, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение смен пользователя.
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу (опционально)
            
        Returns:
            Список смен
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя по telegram_id для получения его id в БД
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return []  # Пользователь не найден, возвращаем пустой список
                
                query = select(Shift).where(Shift.user_id == db_user.id)
                
                if status:
                    query = query.where(Shift.status == status)
                
                query = query.order_by(Shift.start_time.desc())
                
                result = await session.execute(query)
                shifts = result.scalars().all()
                
                # Преобразуем в словари
                shifts_data = []
                for shift in shifts:
                    shift_data = {
                        'id': shift.id,
                        'object_id': shift.object_id,
                        'status': shift.status,
                        'start_time': shift.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_time': shift.end_time.strftime('%Y-%m-%d %H:%M:%S') if shift.end_time else None,
                        'total_hours': float(shift.total_hours) if shift.total_hours else None,
                        'total_payment': float(shift.total_payment) if shift.total_payment else None
                    }
                    shifts_data.append(shift_data)
                
                logger.info(
                    f"User shifts retrieved: user_id={user_id}, status={status}, count={len(shifts_data)}"
                )
                
                return shifts_data
                
        except Exception as e:
            logger.error(
                f"Error getting user shifts: user_id={user_id}, status={status}, error={str(e)}"
            )
        return []
    
    async def get_shift_by_id(self, shift_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение смены по ID.
        
        Args:
            shift_id: ID смены
            
        Returns:
            Словарь с информацией о смене или None
        """
        try:
            async with get_async_session() as session:
                shift = await self._get_shift(session, shift_id)
                
                if not shift:
                    return None
                
                shift_data = {
                    'id': shift.id,
                    'user_id': shift.user_id,
                    'object_id': shift.object_id,
                    'status': shift.status,
                    'start_time': shift.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': shift.end_time.strftime('%Y-%m-%d %H:%M:%S') if shift.end_time else None,
                    'total_hours': float(shift.total_hours) if shift.total_hours else None,
                    'total_payment': float(shift.total_payment) if shift.total_payment else None,
                    'start_coordinates': shift.start_coordinates,
                    'end_coordinates': shift.end_coordinates,
                    'notes': shift.notes
                }
                
                logger.info(
                    f"Shift retrieved: shift_id={shift_id}, user_id={shift.user_id}"
                )
                
                return shift_data
                
        except Exception as e:
            logger.error(
                f"Error getting shift: shift_id={shift_id}, error={str(e)}"
            )
            return None
    
    def get_location_requirements(self) -> Dict[str, Any]:
        """
        Получает требования к геолокации.
        
        Returns:
            Словарь с требованиями
        """
        return self.location_validator.get_location_requirements()
    
    # Вспомогательные методы
    
    async def _get_user(self, session, user_id: int) -> Optional[User]:
        """Получает пользователя по ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def _get_object(self, session, object_id: int) -> Optional[Object]:
        """Получает объект по ID с загрузкой организационной структуры."""
        try:
            from sqlalchemy.orm import selectinload
            from domain.entities.org_structure import OrgStructureUnit
            
            # Загружаем объект с org_unit и всей цепочкой родителей
            def load_org_hierarchy():
                loader = selectinload(Object.org_unit)
                current = loader
                for _ in range(10):  # До 10 уровней иерархии
                    current = current.selectinload(OrgStructureUnit.parent)
                return loader
            
            query = select(Object).options(
                load_org_hierarchy()
            ).where(Object.id == object_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting object {object_id}: {e}")
            return None
    
    async def _get_shift(self, session, shift_id: int) -> Optional[Shift]:
        """Получает смену по ID."""
        try:
            query = select(Shift).where(Shift.id == shift_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting shift {shift_id}: {e}")
            return None
    
    async def _get_active_shift(self, session, user_id: int) -> Optional[Shift]:
        """Получает активную смену пользователя."""
        try:
            query = select(Shift).where(
                and_(
                    Shift.user_id == user_id,
                    Shift.status == 'active',
                    Shift.end_time.is_(None)
                )
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting active shift for user {user_id}: {e}")
        return None
    
    async def get_user_active_shifts(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает активные смены пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Список активных смен
        """
        try:
            async with get_async_session() as session:
                # Находим пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return []
                
                # Получаем активные смены
                active_shifts_query = select(Shift).where(
                    and_(
                        Shift.user_id == db_user.id,
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
                        'start_time': shift.start_time,
                        'hourly_rate': shift.hourly_rate,
                        'status': shift.status
                    })
                
                return shifts_list
                
        except Exception as e:
            logger.error(f"Error getting user active shifts: {e}")
            return []

    async def get_shift_by_id(self, shift_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает смену по ID.
        
        Args:
            shift_id: ID смены
            
        Returns:
            Данные смены или None
        """
        try:
            async with get_async_session() as session:
                query = select(Shift).where(Shift.id == shift_id)
                result = await session.execute(query)
                shift = result.scalar_one_or_none()
                
                if not shift:
                    return None
                
                return {
                    'id': shift.id,
                    'user_id': shift.user_id,
                    'object_id': shift.object_id,
                    'status': shift.status,
                    'start_time': shift.start_time,
                    'end_time': shift.end_time,
                    'total_hours': float(shift.total_hours) if shift.total_hours else None,
                    'total_payment': float(shift.total_payment) if shift.total_payment else None,
                    'start_coordinates': shift.start_coordinates,
                    'end_coordinates': shift.end_coordinates,
                    'notes': shift.notes
                }
                
        except Exception as e:
            logger.error(f"Error getting shift {shift_id}: {e}")
        return None







