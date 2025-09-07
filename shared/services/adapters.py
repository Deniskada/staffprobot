"""Адаптеры для совместимости с существующим кодом."""

from typing import List, Dict, Any, Optional
from apps.bot.services.object_service import ObjectService
from .schedule_service import ScheduleService
from .shift_service import ShiftService


class ObjectServiceAdapter:
    """Адаптер для ObjectService для обратной совместимости."""
    
    def __init__(self):
        """Инициализация адаптера."""
        self._service = ObjectService.get_instance()
    
    def create_object(
        self,
        name: str,
        address: str,
        coordinates: str,
        opening_time: str,
        closing_time: str,
        hourly_rate: float,
        owner_id: int
    ) -> Dict[str, Any]:
        """Создание объекта через общий сервис."""
        return self._service.create_object(
            name, address, coordinates, opening_time, 
            closing_time, hourly_rate, owner_id
        )
    
    def get_user_objects(self, owner_telegram_id: int) -> List[Dict[str, Any]]:
        """Получение объектов пользователя через общий сервис."""
        return self._service.get_user_objects(owner_telegram_id)
    
    def get_object_by_id(self, object_id: int) -> Optional[Dict[str, Any]]:
        """Получение объекта по ID через общий сервис."""
        return self._service.get_object_by_id(object_id)
    
    def update_object(
        self,
        object_id: int,
        field_name: str,
        new_value: Any
    ) -> Dict[str, Any]:
        """Обновление объекта через общий сервис."""
        return self._service.update_object(object_id, field_name, new_value)
    
    def delete_object(self, object_id: int) -> Dict[str, Any]:
        """Удаление объекта через общий сервис."""
        return self._service.delete_object(object_id)


class ScheduleServiceAdapter:
    """Адаптер для ScheduleService для обратной совместимости."""
    
    def __init__(self):
        """Инициализация адаптера."""
        self._service = ScheduleService.get_instance()
    
    async def get_available_time_slots_for_date(
        self, 
        object_id: int, 
        target_date
    ) -> Dict[str, Any]:
        """Получение доступных тайм-слотов через общий сервис."""
        return await self._service.get_available_time_slots_for_date(object_id, target_date)
    
    async def create_scheduled_shift_from_timeslot(
        self,
        user_id: int,
        time_slot_id: int,
        start_time,
        end_time,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Создание запланированной смены через общий сервис."""
        return await self._service.create_scheduled_shift_from_timeslot(user_id, time_slot_id, start_time, end_time, notes)
    
    async def get_user_scheduled_shifts(
        self,
        user_id: int,
        start_date: Optional = None,
        end_date: Optional = None
    ) -> Dict[str, Any]:
        """Получение запланированных смен пользователя через общий сервис."""
        return await self._service.get_user_scheduled_shifts(user_id, start_date, end_date)
    
    async def cancel_scheduled_shift(
        self,
        user_id: int,
        shift_id: int
    ) -> Dict[str, Any]:
        """Отмена запланированной смены через общий сервис."""
        return await self._service.cancel_scheduled_shift(user_id, shift_id)


class ShiftServiceAdapter:
    """Адаптер для ShiftService для обратной совместимости."""
    
    def __init__(self):
        """Инициализация адаптера."""
        self._service = ShiftService.get_instance()
    
    async def open_shift(
        self, 
        user_id: int, 
        object_id: int, 
        coordinates: str
    ) -> Dict[str, Any]:
        """Открытие смены через общий сервис."""
        return await self._service.open_shift(user_id, object_id, coordinates)
    
    async def close_shift(
        self, 
        user_id: int, 
        coordinates: str
    ) -> Dict[str, Any]:
        """Закрытие смены через общий сервис."""
        return await self._service.close_shift(user_id, coordinates)
    
    async def get_user_active_shifts(
        self, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Получение активных смен через общий сервис."""
        return await self._service.get_user_active_shifts(user_id)
    
    async def get_user_shift_history(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Получение истории смен через общий сервис."""
        return await self._service.get_user_shift_history(user_id, limit)
