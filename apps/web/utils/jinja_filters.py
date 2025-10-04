"""
Jinja2 фильтры для приложения
"""
from .static_version import get_static_url_with_version


def static_version_filter(file_path: str) -> str:
    """
    Jinja2 фильтр для добавления версии к статическим файлам
    
    Args:
        file_path: Путь к статическому файлу относительно static/
        
    Returns:
        URL с версией
    """
    return get_static_url_with_version(file_path)


def register_filters(templates):
    """
    Регистрирует фильтры в Jinja2
    
    Args:
        templates: Экземпляр Jinja2Templates
    """
    templates.env.filters['static_version'] = static_version_filter
