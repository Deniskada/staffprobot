"""Единый Jinja2 environment для веб-приложения.

Содержит общий экземпляр `templates` с зарегистрированными кастомными фильтрами.
"""

from fastapi.templating import Jinja2Templates

# Создаем единый экземпляр шаблонизатора
templates = Jinja2Templates(directory="apps/web/templates")

# Регистрируем кастомные фильтры Jinja2
from apps.web.utils.jinja_filters import register_filters

register_filters(templates)

# Добавляем context processor для автоматического добавления enabled_features
from jinja2 import pass_context

@pass_context
def add_enabled_features(context):
    """Добавляет enabled_features из request.state в контекст шаблона."""
    request = context.get('request')
    if request and hasattr(request.state, 'enabled_features'):
        return request.state.enabled_features
    return []

templates.env.globals['enabled_features_from_state'] = add_enabled_features


