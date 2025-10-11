"""
Jinja2 фильтры для приложения
"""
from datetime import datetime
from typing import Optional
from .static_version import get_static_url_with_version
from core.utils.timezone_helper import TimezoneHelper


def static_version_filter(file_path: str) -> str:
    """
    Jinja2 фильтр для добавления версии к статическим файлам
    
    Args:
        file_path: Путь к статическому файлу относительно static/
        
    Returns:
        URL с версией
    """
    return get_static_url_with_version(file_path)


def format_datetime_local(dt: Optional[datetime], timezone_str: str = 'Europe/Moscow', format_str: str = '%d.%m.%Y %H:%M') -> str:
    """
    Jinja2 фильтр для форматирования даты/времени с учетом часового пояса
    
    Args:
        dt: UTC datetime объект
        timezone_str: Временная зона (по умолчанию Europe/Moscow)
        format_str: Формат вывода
        
    Returns:
        Отформатированная строка
    """
    if dt is None:
        return '—'
    
    timezone_helper = TimezoneHelper()
    return timezone_helper.format_local_time(dt, timezone_str, format_str)


def register_filters(templates):
    """
    Регистрирует фильтры и глобальные функции в Jinja2
    
    Args:
        templates: Экземпляр Jinja2Templates
    """
    try:
        # Регистрируем как фильтры
        templates.env.filters['static_version'] = static_version_filter
        templates.env.filters['format_datetime_local'] = format_datetime_local
        
        # ТАКЖЕ регистрируем как глобальные функции (для синтаксиса {{ func(...) }})
        templates.env.globals['static_version'] = static_version_filter
        templates.env.globals['format_datetime_local'] = format_datetime_local
        
        print(f"✅ Фильтры и глобальные функции зарегистрированы: static_version, format_datetime_local")
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
