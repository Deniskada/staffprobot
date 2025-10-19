"""
Jinja2 фильтры для приложения
"""
from datetime import datetime
from typing import Optional, List
from .static_version import get_static_url_with_version
from core.utils.timezone_helper import TimezoneHelper
from core.config.menu_config import MenuConfig


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


def has_feature_filter(enabled_features: List[str], feature_key: str) -> bool:
    """
    Jinja2 фильтр для проверки, включена ли функция.
    
    Usage: {% if enabled_features | has_feature('shared_calendar') %}
    
    Args:
        enabled_features: Список включенных функций пользователя
        feature_key: Ключ проверяемой функции
        
    Returns:
        True если функция включена
    """
    if not enabled_features:
        return False
    return feature_key in enabled_features


def is_menu_visible_filter(enabled_features: List[str], menu_item_key: str) -> bool:
    """
    Jinja2 фильтр для проверки видимости пункта меню.
    
    Usage: {% if enabled_features | is_menu_visible('calendar') %}
    
    Args:
        enabled_features: Список включенных функций пользователя
        menu_item_key: Ключ пункта меню
        
    Returns:
        True если пункт меню должен отображаться
    """
    if not enabled_features:
        enabled_features = []
    return MenuConfig.is_menu_item_visible(menu_item_key, enabled_features)


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
        templates.env.filters['has_feature'] = has_feature_filter
        templates.env.filters['is_menu_visible'] = is_menu_visible_filter
        
        # ТАКЖЕ регистрируем как глобальные функции (для синтаксиса {{ func(...) }})
        templates.env.globals['static_version'] = static_version_filter
        templates.env.globals['format_datetime_local'] = format_datetime_local
        
        print(f"✅ Фильтры зарегистрированы: static_version, format_datetime_local, has_feature, is_menu_visible")
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
