"""Утилиты для работы с временными зонами."""

from datetime import datetime, date
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
    
    def local_to_utc(self, local_datetime: datetime, timezone_str: Optional[str] = None) -> datetime:
        """
        Конвертирует локальное время в UTC.
        
        Args:
            local_datetime: Локальное время
            timezone_str: Временная зона (если не указана, используется по умолчанию)
            
        Returns:
            UTC время
        """
        if local_datetime is None:
            return None
            
        try:
            # Определяем исходную временную зону
            if timezone_str:
                source_tz = pytz.timezone(timezone_str)
            else:
                source_tz = self.default_timezone
            
            # Если время уже с временной зоной
            if local_datetime.tzinfo is not None:
                # Конвертируем в UTC
                return local_datetime.astimezone(pytz.UTC)
            else:
                # Локализуем время в исходной зоне и конвертируем в UTC
                localized_datetime = source_tz.localize(local_datetime)
                return localized_datetime.astimezone(pytz.UTC)
                
        except (pytz.UnknownTimeZoneError, AttributeError) as e:
            logger.error(f"Error converting timezone: {e}")
            return local_datetime
    
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
    
    def get_today_in_timezone(self, timezone_str: str) -> date:
        """
        Получает дату "сегодня" в указанной временной зоне.
        
        Args:
            timezone_str: Временная зона (например, "Europe/Moscow")
            
        Returns:
            Дата "сегодня" в указанной временной зоне
        """
        try:
            target_tz = pytz.timezone(timezone_str)
            now_in_tz = datetime.now(target_tz)
            return now_in_tz.date()
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {timezone_str}, using default")
            return datetime.now(self.default_timezone).date()
    
    def start_of_day_utc(self, local_date: date, timezone_str: Optional[str] = None) -> datetime:
        """
        Возвращает начало дня (00:00:00) в UTC для указанной локальной даты.
        
        Args:
            local_date: Локальная дата
            timezone_str: Временная зона (если не указана, используется по умолчанию)
            
        Returns:
            datetime: Начало дня в UTC
        """
        from datetime import time as dt_time
        
        # Определяем временную зону
        if timezone_str:
            tz = pytz.timezone(timezone_str)
        else:
            tz = self.default_timezone
        
        # Создаём локальное время начала дня
        local_datetime = datetime.combine(local_date, dt_time(0, 0, 0))
        
        # Локализуем и конвертируем в UTC
        localized = tz.localize(local_datetime)
        return localized.astimezone(pytz.UTC)
    
    def end_of_day_utc(self, local_date: date, timezone_str: Optional[str] = None) -> datetime:
        """
        Возвращает конец дня (23:59:59.999999) в UTC для указанной локальной даты.
        
        Args:
            local_date: Локальная дата
            timezone_str: Временная зона (если не указана, используется по умолчанию)
            
        Returns:
            datetime: Конец дня в UTC
        """
        from datetime import time as dt_time, timedelta
        
        # Определяем временную зону
        if timezone_str:
            tz = pytz.timezone(timezone_str)
        else:
            tz = self.default_timezone
        
        # Создаём локальное время конца дня
        local_datetime = datetime.combine(local_date, dt_time(23, 59, 59, 999999))
        
        # Локализуем и конвертируем в UTC
        localized = tz.localize(local_datetime)
        return localized.astimezone(pytz.UTC)
    
    @property
    def local_tz(self):
        """Возвращает локальную временную зону."""
        return self.default_timezone


# Глобальный экземпляр
timezone_helper = TimezoneHelper()


# Функции-обертки для удобства использования
def get_user_timezone(user) -> str:
    """
    Получить timezone пользователя.
    
    Args:
        user: Объект пользователя (User model)
        
    Returns:
        str: Строка timezone (например, 'Europe/Moscow')
    """
    # TODO: В будущем получать из user.timezone
    return timezone_helper.default_timezone_str


def convert_utc_to_local(utc_datetime: datetime, timezone_str: Optional[str] = None) -> datetime:
    """
    Конвертировать UTC время в локальное.
    
    Args:
        utc_datetime: Время в UTC
        timezone_str: Временная зона (опционально)
        
    Returns:
        datetime: Локальное время
    """
    return timezone_helper.utc_to_local(utc_datetime, timezone_str)

