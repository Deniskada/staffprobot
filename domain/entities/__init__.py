"""
Модуль доменных сущностей StaffProBot
"""

# Импортируем модели в правильном порядке
from .base import Base
from .user import User
from .object import Object
from .shift import Shift
from .shift_schedule import ShiftSchedule

__all__ = ["Base", "User", "Object", "Shift", "ShiftSchedule"]
