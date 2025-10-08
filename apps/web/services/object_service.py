"""
Сервис для работы с объектами в веб-интерфейсе
"""

from typing import List, Optional, Dict, Any
from datetime import date, time, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.user import User
from core.logging.logger import logger
from datetime import datetime, time, date
from core.cache.redis_cache import cached
from core.cache.cache_service import CacheService


class ObjectService:
    """Сервис для работы с объектами"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def _get_user_internal_id(self, telegram_id: int) -> Optional[int]:
        """Получить внутренний ID пользователя по Telegram ID"""
        try:
            logger.info(f"_get_user_internal_id called with telegram_id={telegram_id} (type: {type(telegram_id)})")
            query = select(User.id).where(User.telegram_id == telegram_id)
            result = await self.db.execute(query)
            internal_id = result.scalar_one_or_none()
            logger.info(f"Found internal_id={internal_id} for telegram_id={telegram_id}")
            return internal_id
        except Exception as e:
            logger.error(f"Error getting user internal ID for telegram_id {telegram_id}: {e}")
            return None
    
    @cached(ttl=timedelta(minutes=15), key_prefix="objects_by_owner")
    async def get_objects_by_owner(self, telegram_id: int, include_inactive: bool = False) -> List[Object]:
        """Получить все объекты владельца по Telegram ID.
        include_inactive=True возвращает также неактивные объекты.
        """
        try:
            logger.info(f"get_objects_by_owner called with telegram_id={telegram_id} (type: {type(telegram_id)})")
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                logger.warning(f"User with telegram_id {telegram_id} not found")
                return []
            
            query = select(Object).where(
                Object.owner_id == internal_id
            )
            if not include_inactive:
                query = query.where(Object.is_active == True)
            query = query.order_by(Object.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting objects for owner {telegram_id}: {e}")
            raise
    
    async def get_object_by_id(self, object_id: int, telegram_id: int) -> Optional[Object]:
        """Получить объект по ID с проверкой владельца"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return None
            
            query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == internal_id
            )
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting object {object_id} for owner {telegram_id}: {e}")
            raise
    
    async def create_object(self, object_data: Dict[str, Any], telegram_id: int) -> Object:
        """Создать новый объект"""
        try:
            logger.info(f"Creating object for telegram_id {telegram_id} (type: {type(telegram_id)})")
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                raise ValueError(f"User with telegram_id {telegram_id} not found")
            logger.info(f"Found internal_id {internal_id} for telegram_id {telegram_id}")
            
            # Парсим координаты
            coordinates = object_data.get('coordinates')
            if coordinates and isinstance(coordinates, str):
                lat, lon = coordinates.split(',')
                lat, lon = float(lat.strip()), float(lon.strip())
            elif coordinates and isinstance(coordinates, dict):
                lat, lon = coordinates.get('lat', 0.0), coordinates.get('lon', 0.0)
            else:
                lat, lon = 0.0, 0.0
            
            # Создаем объект
            new_object = Object(
                name=object_data['name'],
                owner_id=internal_id,
                address=object_data.get('address', ''),
                coordinates=f"{lat},{lon}",
                opening_time=time.fromisoformat(object_data['opening_time']),
                closing_time=time.fromisoformat(object_data['closing_time']),
                hourly_rate=object_data['hourly_rate'],
                max_distance_meters=object_data.get('max_distance', 500),
                auto_close_minutes=object_data.get('auto_close_minutes', 60),
                available_for_applicants=object_data.get('available_for_applicants', False),
                is_active=object_data.get('is_active', True),
                work_days_mask=object_data.get('work_days_mask', 31),
                schedule_repeat_weeks=object_data.get('schedule_repeat_weeks', 1),
                work_conditions=object_data.get('work_conditions'),
                employee_position=object_data.get('employee_position'),
                shift_tasks=object_data.get('shift_tasks')
            )
            
            self.db.add(new_object)
            await self.db.commit()
            await self.db.refresh(new_object)
            
            # Планируем тайм-слоты до конца года
            try:
                await self.plan_timeslots_for_object(
                    new_object,
                    start_date=date.today(),
                    end_date=date(date.today().year, 12, 31)
                )
                logger.info(f"Planned timeslots for object {new_object.id} until end of year")
            except Exception as e:
                logger.error(f"Error planning timeslots for object {new_object.id}: {e}")
                # Не прерываем создание объекта из-за ошибки планирования
            
            # Обновляем роль владельца на "owner"
            await self._update_owner_role(telegram_id)
            
            logger.info(f"Created object {new_object.id} for owner {telegram_id}")
            
            # Инвалидация кэша объекта
            await CacheService.invalidate_object_cache(new_object.id)
            
            return new_object
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating object for owner {telegram_id}: {e}")
            raise
    
    async def update_object(self, object_id: int, object_data: Dict[str, Any], owner_id: int) -> Optional[Object]:
        """Обновить объект"""
        try:
            # Получаем объект по внутреннему ID владельца
            query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == owner_id
            )
            result = await self.db.execute(query)
            obj = result.scalar_one_or_none()
            if not obj:
                return None
            
            # Обновляем поля
            obj.name = object_data['name']
            obj.address = object_data.get('address', obj.address)
            obj.opening_time = time.fromisoformat(object_data['opening_time'])
            obj.closing_time = time.fromisoformat(object_data['closing_time'])
            obj.timezone = object_data.get('timezone', 'Europe/Moscow')
            obj.hourly_rate = object_data['hourly_rate']
            obj.max_distance_meters = object_data.get('max_distance', obj.max_distance_meters)
            obj.auto_close_minutes = object_data.get('auto_close_minutes', obj.auto_close_minutes)
            obj.is_active = object_data.get('is_active', obj.is_active)
            obj.available_for_applicants = object_data.get('available_for_applicants', obj.available_for_applicants)
            obj.work_days_mask = object_data.get('work_days_mask', obj.work_days_mask)
            obj.schedule_repeat_weeks = object_data.get('schedule_repeat_weeks', obj.schedule_repeat_weeks)
            
            # Обновляем новые поля
            obj.work_conditions = object_data.get('work_conditions', obj.work_conditions)
            obj.employee_position = object_data.get('employee_position', obj.employee_position)
            obj.shift_tasks = object_data.get('shift_tasks', obj.shift_tasks)
            
            logger.info(f"Updating object {object_id} - work_conditions: '{obj.work_conditions}', shift_tasks: {obj.shift_tasks}")
            
            # Обновляем координаты если нужно
            if 'coordinates' in object_data:
                coordinates = object_data['coordinates']
                if isinstance(coordinates, str):
                    lat, lon = coordinates.split(',')
                    lat, lon = float(lat.strip()), float(lon.strip())
                else:
                    lat, lon = coordinates.get('lat', 0.0), coordinates.get('lon', 0.0)
                obj.coordinates = f"{lat},{lon}"
            
            await self.db.commit()
            await self.db.refresh(obj)
            
            logger.info(f"Updated object {object_id} for owner {owner_id}")
            
            # Инвалидация кэша объекта
            await CacheService.invalidate_object_cache(object_id)
            
            return obj
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating object {object_id} for owner {owner_id}: {e}")
            raise
    
    async def update_object_by_manager(self, object_id: int, object_data: Dict[str, Any]) -> Optional[Object]:
        """Обновить объект управляющим (без проверки владельца)"""
        try:
            # Получаем объект напрямую по ID
            query = select(Object).where(Object.id == object_id)
            result = await self.db.execute(query)
            obj = result.scalar_one_or_none()
            
            if not obj:
                return None
            
            # Обновляем поля
            obj.name = object_data['name']
            obj.address = object_data.get('address', obj.address)
            
            # Обработка времени
            if object_data.get('opening_time'):
                if isinstance(object_data['opening_time'], str):
                    obj.opening_time = time.fromisoformat(object_data['opening_time'])
                else:
                    obj.opening_time = object_data['opening_time']
            
            if object_data.get('closing_time'):
                if isinstance(object_data['closing_time'], str):
                    obj.closing_time = time.fromisoformat(object_data['closing_time'])
                else:
                    obj.closing_time = object_data['closing_time']
            
            obj.timezone = object_data.get('timezone', 'Europe/Moscow')
            obj.hourly_rate = object_data['hourly_rate']
            obj.max_distance_meters = object_data.get('max_distance_meters', obj.max_distance_meters)
            obj.is_active = object_data.get('is_active', obj.is_active)
            obj.available_for_applicants = object_data.get('available_for_applicants', obj.available_for_applicants)
            obj.work_days_mask = object_data.get('work_days_mask', obj.work_days_mask)
            obj.schedule_repeat_weeks = object_data.get('schedule_repeat_weeks', obj.schedule_repeat_weeks)
            obj.work_conditions = object_data.get('work_conditions', obj.work_conditions)
            obj.employee_position = object_data.get('employee_position', obj.employee_position)
            obj.shift_tasks = object_data.get('shift_tasks', obj.shift_tasks)
            
            # Обновляем координаты если нужно
            if 'coordinates' in object_data:
                coordinates = object_data['coordinates']
                if isinstance(coordinates, str):
                    lat, lon = coordinates.split(',')
                    lat, lon = float(lat.strip()), float(lon.strip())
                else:
                    lat, lon = coordinates.get('lat', 0.0), coordinates.get('lon', 0.0)
                obj.coordinates = f"{lat},{lon}"
            
            await self.db.commit()
            await self.db.refresh(obj)
            
            logger.info(f"Updated object {object_id} by manager")
            
            # Инвалидация кэша объекта
            await CacheService.invalidate_object_cache(object_id)
            
            return obj
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating object {object_id} by manager: {e}")
            raise
    
    async def delete_object(self, object_id: int, owner_id: int) -> bool:
        """Удалить объект (мягкое удаление)"""
        try:
            # Получаем объект по внутреннему ID владельца
            query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == owner_id
            )
            result = await self.db.execute(query)
            obj = result.scalar_one_or_none()
            if not obj:
                return False
            
            # Мягкое удаление - помечаем как неактивный
            obj.is_active = False
            # Также деактивируем связанные тайм-слоты
            timeslots_query = select(TimeSlot).where(TimeSlot.object_id == object_id)
            timeslots_result = await self.db.execute(timeslots_query)
            timeslots = timeslots_result.scalars().all()
            for slot in timeslots:
                slot.is_active = False

            # Отменяем связанные запланированные смены
            schedules_query = select(ShiftSchedule).where(ShiftSchedule.object_id == object_id)
            schedules_result = await self.db.execute(schedules_query)
            schedules = schedules_result.scalars().all()
            for sched in schedules:
                if sched.status not in ("cancelled", "completed"):
                    sched.status = "cancelled"

            # Отменяем активные/плановые фактические смены (не трогаем завершенные)
            shifts_query = select(Shift).where(Shift.object_id == object_id)
            shifts_result = await self.db.execute(shifts_query)
            shifts = shifts_result.scalars().all()
            for sh in shifts:
                if sh.status not in ("completed", "cancelled"):
                    sh.status = "cancelled"
            await self.db.commit()
            
            # Проверяем, есть ли у владельца другие активные объекты
            await self._check_and_update_owner_role(owner_id)
            
            logger.info(f"Soft deleted object {object_id} for owner {owner_id}")
            
            # Инвалидация кэша объекта
            await CacheService.invalidate_object_cache(object_id)
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting object {object_id} for owner {owner_id}: {e}")
            raise

    async def hard_delete_object(self, object_id: int, owner_id: int) -> bool:
        """Полное удаление объекта из базы данных"""
        try:
            # Получаем объект по внутреннему ID владельца
            query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == owner_id
            )
            result = await self.db.execute(query)
            obj = result.scalar_one_or_none()
            if not obj:
                return False
            
            # Удаляем все связанные сущности в правильном порядке
            
            # 1. Удаляем смены
            shifts_query = select(Shift).where(Shift.object_id == object_id)
            shifts_result = await self.db.execute(shifts_query)
            shifts = shifts_result.scalars().all()
            for shift in shifts:
                await self.db.delete(shift)
            
            # 2. Удаляем расписания смен
            schedules_query = select(ShiftSchedule).where(ShiftSchedule.object_id == object_id)
            schedules_result = await self.db.execute(schedules_query)
            schedules = schedules_result.scalars().all()
            for schedule in schedules:
                await self.db.delete(schedule)
            
            # 3. Удаляем тайм-слоты
            timeslots_query = select(TimeSlot).where(TimeSlot.object_id == object_id)
            timeslots_result = await self.db.execute(timeslots_query)
            timeslots = timeslots_result.scalars().all()
            for timeslot in timeslots:
                await self.db.delete(timeslot)
            
            # 4. Удаляем шаблоны планирования и их тайм-слоты
            from domain.entities.planning_template import PlanningTemplate, TemplateTimeSlot
            
            # Сначала получаем все шаблоны планирования для объекта
            templates_query = select(PlanningTemplate).where(PlanningTemplate.object_id == object_id)
            templates_result = await self.db.execute(templates_query)
            templates = templates_result.scalars().all()
            
            for template in templates:
                # Удаляем тайм-слоты шаблона
                template_timeslots_query = select(TemplateTimeSlot).where(TemplateTimeSlot.template_id == template.id)
                template_timeslots_result = await self.db.execute(template_timeslots_query)
                template_timeslots = template_timeslots_result.scalars().all()
                for template_timeslot in template_timeslots:
                    await self.db.delete(template_timeslot)
                
                # Удаляем сам шаблон
                await self.db.delete(template)
            
            # 5. Удаляем сам объект
            await self.db.delete(obj)
            
            await self.db.commit()
            
            logger.info(f"Hard deleted object {object_id} for owner {owner_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error hard deleting object {object_id} for owner {owner_id}: {e}")
            raise
    
    async def get_object_with_timeslots(self, object_id: int, owner_id: int) -> Optional[Object]:
        """Получить объект с тайм-слотами"""
        try:
            query = select(Object).options(
                selectinload(Object.time_slots)
            ).where(
                Object.id == object_id,
                Object.owner_id == owner_id
            )
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting object {object_id} with timeslots for owner {owner_id}: {e}")
            raise
    
    async def plan_timeslots_for_object(self, obj: Object, start_date: date, end_date: date) -> int:
        """Планирует тайм-слоты для объекта на основе графика работы"""
        try:
            if not obj.work_days_mask or obj.work_days_mask == 0:
                logger.warning(f"Object {obj.id} has no work schedule, skipping timeslot planning")
                return 0
            
            # Определяем рабочие дни из маски
            work_days = []
            for i in range(7):  # 0=Пн, 1=Вт, ..., 6=Вс
                if obj.work_days_mask & (1 << i):
                    work_days.append(i)
            
            if not work_days:
                logger.warning(f"Object {obj.id} has no work days selected")
                return 0
            
            # Планируем тайм-слоты
            planned_count = 0
            current_date = start_date
            
            while current_date <= end_date:
                # Проверяем, является ли текущий день рабочим
                weekday = current_date.weekday()  # 0=Пн, 1=Вт, ..., 6=Вс
                if weekday in work_days:
                    # Создаем тайм-слот на этот день
                    timeslot = TimeSlot(
                        object_id=obj.id,
                        slot_date=current_date,
                        start_time=obj.opening_time,
                        end_time=obj.closing_time,
                        hourly_rate=float(obj.hourly_rate) if obj.hourly_rate else 0,
                        is_active=True
                    )
                    self.db.add(timeslot)
                    planned_count += 1
                
                # Переходим к следующему дню
                current_date += timedelta(days=1)
            
            await self.db.commit()
            logger.info(f"Planned {planned_count} timeslots for object {obj.id} from {start_date} to {end_date}")
            return planned_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error planning timeslots for object {obj.id}: {e}")
            raise
    
    async def _update_owner_role(self, telegram_id: int) -> None:
        """Обновление роли пользователя на 'owner' при создании объекта."""
        try:
            from domain.entities.user import User
            from sqlalchemy import select
            
            # Получаем пользователя
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User with telegram_id {telegram_id} not found")
                return
            
            # Обновляем роль
            user.role = "owner"
            
            # Обновляем массив ролей, если он существует
            if hasattr(user, 'roles') and user.roles:
                if "owner" not in user.roles:
                    user.roles.append("owner")
            else:
                # Если поле roles не существует, создаем его
                user.roles = ["applicant", "owner"]
            
            await self.db.commit()
            logger.info(f"Updated user {telegram_id} role to owner")
            
        except Exception as e:
            logger.error(f"Error updating owner role for user {telegram_id}: {e}")
            # Не поднимаем исключение, чтобы не сломать создание объекта
    
    async def _check_and_update_owner_role(self, owner_id: int) -> None:
        """Проверка и обновление роли владельца при удалении объекта."""
        try:
            from domain.entities.user import User
            from sqlalchemy import select, and_
            
            # Проверяем, есть ли у владельца другие активные объекты
            active_objects_query = select(Object).where(
                and_(
                    Object.owner_id == owner_id,
                    Object.is_active == True
                )
            )
            active_objects_result = await self.db.execute(active_objects_query)
            active_objects = active_objects_result.scalars().all()
            
            # Получаем пользователя
            user_query = select(User).where(User.id == owner_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User with id {owner_id} not found")
                return
            
            # Если нет активных объектов, убираем роль owner
            if not active_objects:
                if user.role == "owner":
                    user.role = "applicant"
                
                # Обновляем массив ролей
                if hasattr(user, 'roles') and user.roles and "owner" in user.roles:
                    user.roles.remove("owner")
                    if not user.roles:  # Если массив стал пустым
                        user.roles = ["applicant"]
                
                await self.db.commit()
                logger.info(f"Removed owner role from user {owner_id} - no active objects")
            else:
                logger.info(f"User {owner_id} still has {len(active_objects)} active objects")
            
        except Exception as e:
            logger.error(f"Error checking owner role for user {owner_id}: {e}")
            # Не поднимаем исключение, чтобы не сломать удаление объекта

    # === МЕТОДЫ ДЛЯ МЕНЕДЖЕРОВ ===
    
    async def get_objects_by_manager(self, telegram_id: int) -> List[Object]:
        """Получить объекты, доступные менеджеру"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            permission_service = ManagerPermissionService(self.db)
            object_ids = await permission_service.get_manager_object_ids(telegram_id)
            
            if not object_ids:
                return []
            
            query = select(Object).where(
                Object.id.in_(object_ids),
                Object.is_active == True
            ).order_by(Object.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting objects for manager {telegram_id}: {e}")
            return []
    
    async def get_object_by_id_for_manager(self, object_id: int, telegram_id: int) -> Optional[Object]:
        """Получить объект по ID для менеджера с проверкой доступа"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            permission_service = ManagerPermissionService(self.db)
            has_access = await permission_service.check_manager_object_access(telegram_id, object_id)
            
            if not has_access:
                return None
            
            query = select(Object).where(Object.id == object_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting object {object_id} for manager {telegram_id}: {e}")
            return None
    
    async def get_timeslots_by_object_for_manager(self, object_id: int, telegram_id: int) -> List[TimeSlot]:
        """Получить тайм-слоты объекта для менеджера"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            permission_service = ManagerPermissionService(self.db)
            has_access = await permission_service.check_manager_object_access(telegram_id, object_id)
            
            if not has_access:
                return []
            
            query = select(TimeSlot).where(
                TimeSlot.object_id == object_id,
                TimeSlot.is_active == True
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting timeslots for object {object_id} for manager {telegram_id}: {e}")
            return []


class TimeSlotService:
    """Сервис для работы с тайм-слотами"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def _get_user_internal_id(self, telegram_id: int) -> Optional[int]:
        """Получить внутренний ID пользователя по Telegram ID"""
        try:
            query = select(User.id).where(User.telegram_id == telegram_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user internal ID for telegram_id {telegram_id}: {e}")
            return None
    
    async def get_timeslots_by_object(
        self,
        object_id: int,
        telegram_id: int,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "slot_date",
        sort_order: str = "desc"
    ) -> List[TimeSlot]:
        """Получить тайм-слоты объекта с проверкой владельца, фильтрацией и сортировкой"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                logger.warning(f"No internal ID found for telegram_id {telegram_id}")
                return []
            
            # Сначала проверяем, что объект принадлежит владельцу
            object_query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == internal_id
            )
            object_result = await self.db.execute(object_query)
            if not object_result.scalar_one_or_none():
                logger.warning(f"Object {object_id} not found or not owned by user {internal_id}")
                return []
            
            # Нормализуем входные параметры
            sort_by_norm = (sort_by or "slot_date").strip().lower()
            sort_order_norm = (sort_order or "desc").strip().lower()
            allowed_sort_by = {"slot_date", "start_time", "hourly_rate"}
            if sort_by_norm not in allowed_sort_by:
                sort_by_norm = "slot_date"
            if sort_order_norm not in {"asc", "desc"}:
                sort_order_norm = "desc"

            # Приводим пустые строки к None для дат
            date_from_val = (date_from or "").strip() or None
            date_to_val = (date_to or "").strip() or None

            # Строим запрос с фильтрацией
            query = select(TimeSlot).where(
                TimeSlot.object_id == object_id,
                TimeSlot.is_active == True
            )
            
            # Добавляем фильтрацию по датам
            if date_from_val:
                try:
                    from_date = date.fromisoformat(date_from_val)
                    query = query.where(TimeSlot.slot_date >= from_date)
                except ValueError:
                    logger.warning(f"Invalid date_from format: {date_from_val}")
            
            if date_to_val:
                try:
                    to_date = date.fromisoformat(date_to_val)
                    query = query.where(TimeSlot.slot_date <= to_date)
                except ValueError:
                    logger.warning(f"Invalid date_to format: {date_to_val}")
            
            # Добавляем сортировку
            if sort_by_norm == "slot_date":
                if sort_order_norm == "desc":
                    query = query.order_by(TimeSlot.slot_date.desc(), TimeSlot.start_time.desc())
                else:
                    query = query.order_by(TimeSlot.slot_date.asc(), TimeSlot.start_time.asc())
            elif sort_by_norm == "start_time":
                if sort_order_norm == "desc":
                    query = query.order_by(TimeSlot.start_time.desc(), TimeSlot.slot_date.desc())
                else:
                    query = query.order_by(TimeSlot.start_time.asc(), TimeSlot.slot_date.asc())
            elif sort_by_norm == "hourly_rate":
                if sort_order_norm == "desc":
                    query = query.order_by(TimeSlot.hourly_rate.desc(), TimeSlot.slot_date.desc())
                else:
                    query = query.order_by(TimeSlot.hourly_rate.asc(), TimeSlot.slot_date.asc())
            else:
                # По умолчанию сортируем по дате
                query = query.order_by(TimeSlot.slot_date.desc(), TimeSlot.start_time.desc())
            
            result = await self.db.execute(query)
            timeslots = result.scalars().all()
            
            logger.info(
                f"Found {len(timeslots)} timeslots for object {object_id} with filters: "
                f"date_from={date_from_val}, date_to={date_to_val}, sort_by={sort_by_norm}, sort_order={sort_order_norm}"
            )
            
            return timeslots
        except Exception as e:
            logger.error(f"Error getting timeslots for object {object_id}: {e}")
            raise
    
    async def create_timeslot(self, timeslot_data: Dict[str, Any], object_id: int, telegram_id: int) -> Optional[TimeSlot]:
        """Создать новый тайм-слот с защитой от дубликатов"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return None
            
            # Проверяем, что объект принадлежит владельцу
            object_query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == internal_id
            )
            object_result = await self.db.execute(object_query)
            if not object_result.scalar_one_or_none():
                return None
            
            # Проверяем дубликаты: тот же объект, дата, start_time, end_time
            duplicate_q = select(TimeSlot).where(
                TimeSlot.object_id == object_id,
                TimeSlot.slot_date == timeslot_data.get('slot_date', datetime.now().date()),
                TimeSlot.start_time == time.fromisoformat(timeslot_data['start_time']),
                TimeSlot.end_time == time.fromisoformat(timeslot_data['end_time'])
            )
            dup_res = await self.db.execute(duplicate_q)
            if dup_res.scalar_one_or_none():
                logger.info(f"Skip duplicate timeslot for object {object_id} on {timeslot_data.get('slot_date')} {timeslot_data.get('start_time')}-{timeslot_data.get('end_time')}")
                return None

            # Создаем тайм-слот
            new_timeslot = TimeSlot(
                object_id=object_id,
                slot_date=timeslot_data.get('slot_date', datetime.now().date()),
                start_time=time.fromisoformat(timeslot_data['start_time']),
                end_time=time.fromisoformat(timeslot_data['end_time']),
                hourly_rate=timeslot_data.get('hourly_rate'),
                max_employees=timeslot_data.get('max_employees', 1),
                is_additional=timeslot_data.get('is_additional', False),
                is_active=timeslot_data.get('is_active', True),
                notes=timeslot_data.get('notes', '')
            )
            
            self.db.add(new_timeslot)
            await self.db.commit()
            await self.db.refresh(new_timeslot)
            
            logger.info(f"Created timeslot {new_timeslot.id} for object {object_id}")
            
            # Инвалидация кэша календаря
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_timeslots:*")
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")  # API responses
            
            return new_timeslot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating timeslot for object {object_id}: {e}")
            raise
    
    async def get_timeslot_by_id(self, timeslot_id: int, telegram_id: int) -> Optional[TimeSlot]:
        """Получить тайм-слот по ID с проверкой владельца"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return None
            
            # Получаем тайм-слот с проверкой владельца через объект
            query = select(TimeSlot).join(Object).where(
                TimeSlot.id == timeslot_id,
                Object.owner_id == internal_id
            )
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting timeslot {timeslot_id} for owner {telegram_id}: {e}")
            raise
    
    async def update_timeslot(self, timeslot_id: int, timeslot_data: Dict[str, Any], telegram_id: int) -> Optional[TimeSlot]:
        """Обновить тайм-слот"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return None
            
            # Получаем тайм-слот с проверкой владельца через объект
            query = select(TimeSlot).join(Object).where(
                TimeSlot.id == timeslot_id,
                Object.owner_id == internal_id
            )
            
            result = await self.db.execute(query)
            timeslot = result.scalar_one_or_none()
            if not timeslot:
                return None
            
            # Обновляем поля
            timeslot.slot_date = timeslot_data.get('slot_date', timeslot.slot_date)
            timeslot.start_time = time.fromisoformat(timeslot_data['start_time'])
            timeslot.end_time = time.fromisoformat(timeslot_data['end_time'])
            timeslot.hourly_rate = timeslot_data.get('hourly_rate', timeslot.hourly_rate)
            timeslot.max_employees = timeslot_data.get('max_employees', timeslot.max_employees)
            timeslot.is_additional = timeslot_data.get('is_additional', timeslot.is_additional)
            timeslot.is_active = timeslot_data.get('is_active', timeslot.is_active)
            timeslot.notes = timeslot_data.get('notes', timeslot.notes)
            
            await self.db.commit()
            await self.db.refresh(timeslot)
            
            logger.info(f"Updated timeslot {timeslot_id}")
            
            # Инвалидация кэша календаря
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_timeslots:*")
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")  # API responses
            
            return timeslot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating timeslot {timeslot_id}: {e}")
            raise
    
    async def delete_timeslot(self, timeslot_id: int, telegram_id: int) -> bool:
        """Удалить тайм-слот"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return False
            
            # Получаем тайм-слот с проверкой владельца через объект
            query = select(TimeSlot).join(Object).where(
                TimeSlot.id == timeslot_id,
                Object.owner_id == internal_id
            )
            
            result = await self.db.execute(query)
            timeslot = result.scalar_one_or_none()
            if not timeslot:
                return False
            
            # Мягкое удаление
            timeslot.is_active = False
            await self.db.commit()
            
            logger.info(f"Soft deleted timeslot {timeslot_id}")
            
            # Инвалидация кэша календаря
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_timeslots:*")
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")  # API responses
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting timeslot {timeslot_id}: {e}")
            raise
    
    async def get_timeslots_by_month(
        self, 
        year: int, 
        month: int, 
        owner_telegram_id: int,
        object_id: Optional[int] = None
    ) -> List[TimeSlot]:
        """Получение тайм-слотов за месяц для владельца."""
        try:
            # Получаем внутренний ID владельца
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await self.db.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                logger.warning(f"Owner not found for telegram_id: {owner_telegram_id}")
                return []
            
            logger.info(f"Found owner: {owner.id} for telegram_id: {owner_telegram_id}")
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == owner.id)
            if object_id:
                objects_query = objects_query.where(Object.id == object_id)
            
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            object_ids = [obj.id for obj in objects]
            
            logger.info(f"Found objects: {object_ids} for owner {owner.id}")
            
            if not object_ids:
                return []
            
            # Получаем тайм-слоты
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            logger.info(f"Looking for timeslots between {start_date} and {end_date}")
            
            timeslots_query = select(TimeSlot).options(
                selectinload(TimeSlot.object)
            ).where(
                and_(
                    TimeSlot.object_id.in_(object_ids),
                    TimeSlot.slot_date >= start_date,
                    TimeSlot.slot_date < end_date,
                    TimeSlot.is_active == True
                )
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
            
            timeslots_result = await self.db.execute(timeslots_query)
            timeslots = timeslots_result.scalars().all()
            
            logger.info(f"Found {len(timeslots)} timeslots")
            return timeslots
            
        except Exception as e:
            logger.error(f"Error getting timeslots by month: {e}")
            return []
    
    # === МЕТОДЫ ДЛЯ МЕНЕДЖЕРОВ ===
    
    async def create_timeslot_for_manager(self, timeslot_data: Dict[str, Any], object_id: int, telegram_id: int) -> Optional[TimeSlot]:
        """Создать тайм-слот для менеджера"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            permission_service = ManagerPermissionService(self.db)
            has_access = await permission_service.check_manager_object_access(telegram_id, object_id)
            
            if not has_access:
                return None
            
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return None
            
            # Создаем тайм-слот
            new_timeslot = TimeSlot(
                object_id=object_id,
                slot_date=timeslot_data.get('slot_date', datetime.now().date()),
                start_time=time.fromisoformat(timeslot_data['start_time']),
                end_time=time.fromisoformat(timeslot_data['end_time']),
                hourly_rate=timeslot_data.get('hourly_rate'),
                max_employees=timeslot_data.get('max_employees', 1),
                is_additional=timeslot_data.get('is_additional', False),
                is_active=timeslot_data.get('is_active', True),
                notes=timeslot_data.get('notes', '')
            )
            
            self.db.add(new_timeslot)
            await self.db.commit()
            await self.db.refresh(new_timeslot)
            
            logger.info(f"Created timeslot {new_timeslot.id} for object {object_id} by manager {telegram_id}")
            
            # Инвалидация кэша календаря
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_timeslots:*")
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")  # API responses
            
            return new_timeslot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating timeslot for object {object_id} by manager {telegram_id}: {e}")
            raise
    
    async def get_timeslot_by_id_for_manager(self, timeslot_id: int, telegram_id: int) -> Optional[TimeSlot]:
        """Получить тайм-слот по ID для менеджера"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            # Получаем тайм-слот
            query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
            result = await self.db.execute(query)
            timeslot = result.scalar_one_or_none()
            
            if not timeslot:
                return None
            
            # Проверяем доступ к объекту
            permission_service = ManagerPermissionService(self.db)
            has_access = await permission_service.check_manager_object_access(telegram_id, timeslot.object_id)
            
            if not has_access:
                return None
            
            return timeslot
            
        except Exception as e:
            logger.error(f"Error getting timeslot {timeslot_id} for manager {telegram_id}: {e}")
            raise
    
    async def update_timeslot_for_manager(self, timeslot_id: int, timeslot_data: Dict[str, Any], telegram_id: int) -> Optional[TimeSlot]:
        """Обновить тайм-слот для менеджера"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            # Получаем тайм-слот
            query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
            result = await self.db.execute(query)
            timeslot = result.scalar_one_or_none()
            
            if not timeslot:
                return None
            
            # Проверяем доступ к объекту
            permission_service = ManagerPermissionService(self.db)
            has_access = await permission_service.check_manager_object_access(telegram_id, timeslot.object_id)
            
            if not has_access:
                return None
            
            # Обновляем поля
            timeslot.slot_date = timeslot_data.get('slot_date', timeslot.slot_date)
            timeslot.start_time = time.fromisoformat(timeslot_data['start_time'])
            timeslot.end_time = time.fromisoformat(timeslot_data['end_time'])
            timeslot.hourly_rate = timeslot_data.get('hourly_rate', timeslot.hourly_rate)
            timeslot.max_employees = timeslot_data.get('max_employees', timeslot.max_employees)
            timeslot.is_additional = timeslot_data.get('is_additional', timeslot.is_additional)
            timeslot.is_active = timeslot_data.get('is_active', timeslot.is_active)
            timeslot.notes = timeslot_data.get('notes', timeslot.notes)
            
            await self.db.commit()
            await self.db.refresh(timeslot)
            
            logger.info(f"Updated timeslot {timeslot_id} by manager {telegram_id}")
            
            # Инвалидация кэша календаря
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_timeslots:*")
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")  # API responses
            
            return timeslot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating timeslot {timeslot_id} by manager {telegram_id}: {e}")
            raise
    
    async def delete_timeslot_for_manager(self, timeslot_id: int, telegram_id: int) -> bool:
        """Удалить тайм-слот для менеджера"""
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            
            # Получаем тайм-слот
            query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
            result = await self.db.execute(query)
            timeslot = result.scalar_one_or_none()
            
            if not timeslot:
                return False
            
            # Проверяем доступ к объекту
            permission_service = ManagerPermissionService(self.db)
            has_access = await permission_service.check_manager_object_access(telegram_id, timeslot.object_id)
            
            if not has_access:
                return False
            
            # Мягкое удаление
            timeslot.is_active = False
            await self.db.commit()
            
            logger.info(f"Soft deleted timeslot {timeslot_id} by manager {telegram_id}")
            
            # Инвалидация кэша календаря
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_timeslots:*")
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")  # API responses
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting timeslot {timeslot_id} by manager {telegram_id}: {e}")
            raise
