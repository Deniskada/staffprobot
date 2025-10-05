"""Единый Jinja2 environment для веб-приложения.

Содержит общий экземпляр `templates` с зарегистрированными кастомными фильтрами.
"""

from fastapi.templating import Jinja2Templates

# Создаем единый экземпляр шаблонизатора
templates = Jinja2Templates(directory="apps/web/templates")

# Регистрируем кастомные фильтры Jinja2
from apps.web.utils.jinja_filters import register_filters

register_filters(templates)


