"""Утилиты для работы с временными зонами."""

from datetime import datetime
from typing import Optional
import pytz
from core.config.settings import settings
from core.logging.logger import logger


class TimezoneHelper:
    """Помощник для работы с временными зонами."""
    
    def __init__(self, default_timezone: str = None):
        """
        Инициализация помощника временных зон.
        
        Args:
            default_timezone: Временная зона по умолчанию
        """
        self.default_timezone_str = default_timezone or settings.default_timezone
        try:
            self.default_timezone = pytz.timezone(self.default_timezone_str)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {self.default_timezone_str}, using UTC")
            self.default_timezone = pytz.UTC
    
    def utc_to_local(self, utc_datetime: datetime, timezone_str: Optional[str] = None) -> datetime:
        """
        Конвертирует UTC время в локальное время.
        
        Args:
            utc_datetime: UTC время
            timezone_str: Временная зона (если не указана, используется по умолчанию)
            
        Returns:
            Локальное время
        """
        if utc_datetime is None:
            return None
            
        try:
            # Определяем целевую временную зону
            if timezone_str:
                target_tz = pytz.timezone(timezone_str)
            else:
                target_tz = self.default_timezone
            
            # Если время уже с временной зоной
            if utc_datetime.tzinfo is not None:
                # Конвертируем в целевую зону
                return utc_datetime.astimezone(target_tz)
            else:
                # Считаем что время в UTC и добавляем информацию о зоне
                utc_datetime = pytz.UTC.localize(utc_datetime)
                return utc_datetime.astimezone(target_tz)
                
        except (pytz.UnknownTimeZoneError, AttributeError) as e:
            logger.error(f"Error converting timezone: {e}")
            return utc_datetime
    
    def format_local_time(self, utc_datetime: datetime, timezone_str: Optional[str] = None, format_str: str = "%H:%M:%S") -> str:
        """
        Форматирует UTC время как локальное время.
        
        Args:
            utc_datetime: UTC время
            timezone_str: Временная зона
            format_str: Формат времени
            
        Returns:
            Отформатированная строка времени
        """
        if utc_datetime is None:
            return "Неизвестно"
            
        local_time = self.utc_to_local(utc_datetime, timezone_str)
        if local_time:
            return local_time.strftime(format_str)
        return "Ошибка"
    
    def get_user_timezone(self, user_id: int) -> str:
        """
        Получает временную зону пользователя.
        
        В будущем можно добавить сохранение зоны пользователя в БД.
        Пока возвращает зону по умолчанию.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Строка временной зоны
        """
        # TODO: В будущем получать из профиля пользователя
        return self.default_timezone_str


# Глобальный экземпляр
timezone_helper = TimezoneHelper()
