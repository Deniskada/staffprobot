#!/usr/bin/env python3
"""
Независимые сервисы для API без FastAPI
"""
import asyncio
from datetime import datetime, time
from decimal import Decimal
from typing import List, Optional, Dict, Any

# Простые модели данных
class User:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.telegram_id = kwargs.get('telegram_id')
        self.username = kwargs.get('username')
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.phone = kwargs.get('phone')
        self.role = kwargs.get('role')
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())

class Object:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.owner_id = kwargs.get('owner_id')
        self.address = kwargs.get('address')
        self.coordinates = kwargs.get('coordinates')
        self.opening_time = kwargs.get('opening_time')
        self.closing_time = kwargs.get('closing_time')
        self.hourly_rate = kwargs.get('hourly_rate')
        self.required_employees = kwargs.get('required_employees')
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())

class Shift:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.object_id = kwargs.get('object_id')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.status = kwargs.get('status')
        self.start_coordinates = kwargs.get('start_coordinates')
        self.end_coordinates = kwargs.get('end_coordinates')
        self.total_hours = kwargs.get('total_hours')
        self.hourly_rate = kwargs.get('hourly_rate')
        self.total_payment = kwargs.get('total_payment')
        self.notes = kwargs.get('notes')
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())


class MockUserService:
    """Сервис для работы с пользователями (заглушка)."""
    
    def __init__(self):
        self.users = []
        self._counter = 0
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        """Создает нового пользователя."""
        self._counter += 1
        user = User(
            id=self._counter,
            **user_data
        )
        self.users.append(user)
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получает пользователя по ID."""
        for user in self.users:
            if user.id == user_id:
                return user
        return None
    
    async def get_all_users(self) -> List[User]:
        """Получает всех пользователей."""
        return self.users
    
    async def get_users_by_role(self, role: str) -> List[User]:
        """Получает пользователей по роли."""
        return [user for user in self.users if user.role == role]


class MockObjectService:
    """Сервис для работы с объектами (заглушка)."""
    
    def __init__(self):
        self.objects = []
        self._counter = 0
    
    async def create_object(self, object_data: Dict[str, Any]) -> Optional[Object]:
        """Создает новый объект."""
        self._counter += 1
        obj = Object(
            id=self._counter,
            **object_data
        )
        self.objects.append(obj)
        return obj
    
    async def get_object(self, object_id: int) -> Optional[Object]:
        """Получает объект по ID."""
        for obj in self.objects:
            if obj.id == object_id:
                return obj
        return None
    
    async def get_all_objects(self) -> List[Object]:
        """Получает все объекты."""
        return self.objects
    
    async def get_objects_by_owner(self, owner_id: int) -> List[Object]:
        """Получает объекты по владельцу."""
        return [obj for obj in self.objects if obj.owner_id == owner_id]


class MockShiftService:
    """Сервис для работы со сменами (заглушка)."""
    
    def __init__(self):
        self.shifts = []
        self._counter = 0
    
    async def create_shift(self, shift_data: Dict[str, Any]) -> Optional[Shift]:
        """Создает новую смену."""
        self._counter += 1
        shift = Shift(
            id=self._counter,
            **shift_data
        )
        self.shifts.append(shift)
        return shift
    
    async def get_shift(self, shift_id: int) -> Optional[Shift]:
        """Получает смену по ID."""
        for shift in self.shifts:
            if shift.id == shift_id:
                return shift
        return None
    
    async def get_all_shifts(self) -> List[Shift]:
        """Получает все смены."""
        return self.shifts
    
    async def get_shifts_by_user(self, user_id: int) -> List[Shift]:
        """Получает смены по пользователю."""
        return [shift for shift in self.shifts if shift.user_id == user_id]
    
    async def get_shifts_by_object(self, object_id: int) -> List[Shift]:
        """Получает смены по объекту."""
        return [shift for shift in self.shifts if shift.object_id == object_id]
    
    async def get_shifts_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Shift]:
        """Получает смены по диапазону дат."""
        return [shift for shift in self.shifts 
                if start_date <= shift.start_time <= end_date]


# Глобальные экземпляры сервисов
user_service = MockUserService()
object_service = MockObjectService()
shift_service = MockShiftService()


async def init_mock_data():
    """Инициализирует тестовые данные."""
    # Создаем тестового пользователя
    user_data = {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Тест",
        "last_name": "Пользователь",
        "phone": "+79001234567",
        "role": "employee",
        "is_active": True
    }
    await user_service.create_user(user_data)
    
    # Создаем тестовый объект
    object_data = {
        "name": "Тестовый объект",
        "owner_id": 1,
        "address": "ул. Тестовая, 1",
        "coordinates": "55.7558,37.6176",
        "opening_time": time(9, 0),
        "closing_time": time(18, 0),
        "hourly_rate": Decimal("500.00"),
        "required_employees": "Охранник, уборщик",
        "is_active": True
    }
    await object_service.create_object(object_data)
    
    # Создаем тестовую смену
    shift_data = {
        "user_id": 1,
        "object_id": 1,
        "start_time": datetime.now(),
        "status": "active",
        "start_coordinates": "55.7558,37.6176",
        "hourly_rate": Decimal("500.00"),
        "notes": "Тестовая смена"
    }
    await shift_service.create_shift(shift_data)
    
    print("✅ Тестовые данные инициализированы")


if __name__ == "__main__":
    # Тестируем сервисы
    asyncio.run(init_mock_data())
    
    print(f"👥 Пользователей: {len(user_service.users)}")
    print(f"🏢 Объектов: {len(object_service.objects)}")
    print(f"⏰ Смен: {len(shift_service.shifts)}")
