"""
Сервис для работы с объектами в веб-интерфейсе
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from domain.entities.user import User
from core.logging.logger import logger
from datetime import datetime, time, date


class ObjectService:
    """Сервис для работы с объектами"""
    
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
    
    async def get_objects_by_owner(self, telegram_id: int) -> List[Object]:
        """Получить все объекты владельца по Telegram ID"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                logger.warning(f"User with telegram_id {telegram_id} not found")
                return []
            
            query = select(Object).where(
                Object.owner_id == internal_id,
                Object.is_active == True
            ).order_by(Object.created_at.desc())
            
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
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                raise ValueError(f"User with telegram_id {telegram_id} not found")
            
            # Парсим координаты
            coordinates = object_data.get('coordinates', '0.0,0.0')
            if isinstance(coordinates, str):
                lat, lon = coordinates.split(',')
                lat, lon = float(lat.strip()), float(lon.strip())
            else:
                lat, lon = coordinates.get('lat', 0.0), coordinates.get('lon', 0.0)
            
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
                available_for_applicants=object_data.get('available_for_applicants', False),
                is_active=object_data.get('is_active', True)
            )
            
            self.db.add(new_object)
            await self.db.commit()
            await self.db.refresh(new_object)
            
            logger.info(f"Created object {new_object.id} for owner {telegram_id}")
            return new_object
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating object for owner {telegram_id}: {e}")
            raise
    
    async def update_object(self, object_id: int, object_data: Dict[str, Any], owner_id: int) -> Optional[Object]:
        """Обновить объект"""
        try:
            # Получаем объект
            obj = await self.get_object_by_id(object_id, owner_id)
            if not obj:
                return None
            
            # Обновляем поля
            obj.name = object_data['name']
            obj.address = object_data.get('address', obj.address)
            obj.opening_time = time.fromisoformat(object_data['opening_time'])
            obj.closing_time = time.fromisoformat(object_data['closing_time'])
            obj.hourly_rate = object_data['hourly_rate']
            obj.max_distance_meters = object_data.get('max_distance', obj.max_distance_meters)
            obj.is_active = object_data.get('is_active', obj.is_active)
            
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
            return obj
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating object {object_id} for owner {owner_id}: {e}")
            raise
    
    async def delete_object(self, object_id: int, owner_id: int) -> bool:
        """Удалить объект (мягкое удаление)"""
        try:
            obj = await self.get_object_by_id(object_id, owner_id)
            if not obj:
                return False
            
            # Мягкое удаление - помечаем как неактивный
            obj.is_active = False
            await self.db.commit()
            
            logger.info(f"Soft deleted object {object_id} for owner {owner_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting object {object_id} for owner {owner_id}: {e}")
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
    
    async def get_timeslots_by_object(self, object_id: int, telegram_id: int) -> List[TimeSlot]:
        """Получить тайм-слоты объекта с проверкой владельца"""
        try:
            # Получаем внутренний ID пользователя
            internal_id = await self._get_user_internal_id(telegram_id)
            if not internal_id:
                return []
            
            # Сначала проверяем, что объект принадлежит владельцу
            object_query = select(Object).where(
                Object.id == object_id,
                Object.owner_id == internal_id
            )
            object_result = await self.db.execute(object_query)
            if not object_result.scalar_one_or_none():
                return []
            
            # Получаем тайм-слоты
            query = select(TimeSlot).where(
                TimeSlot.object_id == object_id,
                TimeSlot.is_active == True
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting timeslots for object {object_id}: {e}")
            raise
    
    async def create_timeslot(self, timeslot_data: Dict[str, Any], object_id: int, telegram_id: int) -> Optional[TimeSlot]:
        """Создать новый тайм-слот"""
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
                return []
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == owner.id)
            if object_id:
                objects_query = objects_query.where(Object.id == object_id)
            
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            object_ids = [obj.id for obj in objects]
            
            if not object_ids:
                return []
            
            # Получаем тайм-слоты
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
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
            return timeslots_result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting timeslots by month: {e}")
            return []
