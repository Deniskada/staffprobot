"""Базовый класс для всех сервисов с Singleton паттерном."""

from typing import Dict, Any
from core.logging.logger import logger


class BaseService:
    """Базовый класс для всех сервисов с Singleton паттерном."""
    
    _instances: Dict[type, 'BaseService'] = {}
    
    def __new__(cls):
        """Singleton паттерн для предотвращения множественной инициализации."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._instances[cls]._initialized = False
        return cls._instances[cls]
    
    def __init__(self):
        """Инициализация сервиса."""
        if not self._initialized:
            self._initialize_service()
            self._initialized = True
    
    def _initialize_service(self):
        """Метод для переопределения в наследниках."""
        logger.info(f"{self.__class__.__name__} initialized")
    
    @classmethod
    def get_instance(cls):
        """Получение экземпляра сервиса."""
        return cls()
    
    @classmethod
    def clear_instance(cls):
        """Очистка экземпляра сервиса (для тестов)."""
        if cls in cls._instances:
            del cls._instances[cls]


