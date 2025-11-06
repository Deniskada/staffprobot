"""Единый Jinja2 environment для веб-приложения.

Содержит общий экземпляр `templates` с зарегистрированными кастомными фильтрами.
"""

from fastapi.templating import Jinja2Templates
from core.config.settings import settings

# Создаем единый экземпляр шаблонизатора
templates = Jinja2Templates(directory="apps/web/templates")

# Регистрируем кастомные фильтры Jinja2
from apps.web.utils.jinja_filters import register_filters

register_filters(templates)

# Добавляем settings в глобальные переменные Jinja2
templates.env.globals['settings'] = settings

# Добавляем web_timezone_helper в глобальные переменные Jinja2
from apps.web.utils.timezone_utils import web_timezone_helper
templates.env.globals['web_timezone_helper'] = web_timezone_helper


