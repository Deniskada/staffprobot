"""Утилиты для работы с часовыми поясами в веб-интерфейсе."""

from datetime import datetime
from typing import Optional
import pytz
from core.logging.logger import logger


class WebTimezoneHelper:
    """Помощник для работы с часовыми поясами в веб-интерфейсе."""
    
    @staticmethod
    def format_datetime_with_timezone(utc_datetime: datetime, timezone_str: str = "Europe/Moscow", 
                                    format_str: str = "%d.%m.%Y %H:%M") -> str:
        """
        Форматирует UTC время в локальное время объекта.
        
        Args:
            utc_datetime: UTC время
            timezone_str: Часовой пояс объекта
            format_str: Формат времени
            
        Returns:
            Отформатированная строка времени
        """
        if utc_datetime is None:
            return "Неизвестно"
            
        try:
            # Получаем часовой пояс объекта
            object_tz = pytz.timezone(timezone_str)
            
            # Если время уже с временной зоной
            if utc_datetime.tzinfo is not None:
                # Конвертируем в часовой пояс объекта
                local_time = utc_datetime.astimezone(object_tz)
            else:
                # Считаем что время в UTC и добавляем информацию о зоне
                utc_datetime = pytz.UTC.localize(utc_datetime)
                local_time = utc_datetime.astimezone(object_tz)
            
            return local_time.strftime(format_str)
            
        except (pytz.UnknownTimeZoneError, AttributeError) as e:
            logger.error(f"Error converting timezone {timezone_str}: {e}")
            # Fallback: показываем время как есть
            if hasattr(utc_datetime, 'strftime'):
                return utc_datetime.strftime(format_str)
            else:
                return str(utc_datetime)
    
    @staticmethod
    def format_time_with_timezone(utc_datetime: datetime, timezone_str: str = "Europe/Moscow", 
                                format_str: str = "%H:%M") -> str:
        """
        Форматирует только время (без даты) в локальном часовом поясе.
        
        Args:
            utc_datetime: UTC время
            timezone_str: Часовой пояс объекта
            format_str: Формат времени
            
        Returns:
            Отформатированная строка времени
        """
        return WebTimezoneHelper.format_datetime_with_timezone(
            utc_datetime, timezone_str, format_str
        )
    
    @staticmethod
    def get_object_timezone(object_data: dict) -> str:
        """
        Получает часовой пояс объекта.
        
        Args:
            object_data: Данные объекта
            
        Returns:
            Строка часового пояса
        """
        if not object_data:
            return "Europe/Moscow"
        
        return object_data.get('timezone', 'Europe/Moscow')


# Глобальный экземпляр
web_timezone_helper = WebTimezoneHelper()
