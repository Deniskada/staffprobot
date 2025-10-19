"""
Middleware для автоматического добавления enabled_features в контекст шаблонов.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from core.database.session import get_async_session
from shared.services.system_features_service import SystemFeaturesService
from apps.web.middleware.role_middleware import get_user_id_from_current_user
from apps.web.middleware.auth_middleware import get_current_user
from core.logging.logger import logger


class FeaturesMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматического добавления enabled_features в request.state."""
    
    async def dispatch(self, request: Request, call_next):
        """Обработка запроса - добавление enabled_features в request.state."""
        
        # Инициализируем пустым списком
        request.state.enabled_features = []
        
        # Проверяем, что это owner-роут
        if request.url.path.startswith('/owner/'):
            try:
                # Получаем current_user
                current_user = await get_current_user(request)
                
                if current_user and isinstance(current_user, dict):
                    async with get_async_session() as session:
                        # Получаем user_id
                        user_id = await get_user_id_from_current_user(current_user, session)
                        
                        if user_id:
                            # Получаем enabled_features
                            service = SystemFeaturesService()
                            enabled_features = await service.get_enabled_features(session, user_id)
                            
                            # Добавляем в request.state
                            request.state.enabled_features = enabled_features or []
                            
                            logger.debug(
                                f"FeaturesMiddleware: User {user_id} path {request.url.path} "
                                f"features: {request.state.enabled_features}"
                            )
            except Exception as e:
                logger.error(f"FeaturesMiddleware error: {e}", exc_info=True)
                # Оставляем пустой список при ошибке
                request.state.enabled_features = []
        
        response = await call_next(request)
        return response


async def get_enabled_features_for_template(
    request: Request,
    current_user: dict,
    session: AsyncSession
) -> List[str]:
    """
    Получить список включенных функций для использования в шаблонах.
    
    Args:
        request: HTTP запрос
        current_user: Данные текущего пользователя
        session: Сессия БД
        
    Returns:
        Список ключей включенных функций
    """
    try:
        # Если пользователь не авторизован или это не владелец
        if not current_user:
            return []
        
        # Проверяем роль
        roles = current_user.get('roles', [current_user.get('role')])
        if 'owner' not in roles and 'superadmin' not in roles:
            return []
        
        # Получаем user_id
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            return []
        
        # Получаем включенные функции
        features_service = SystemFeaturesService()
        enabled_features = await features_service.get_enabled_features(session, user_id)
        
        return enabled_features or []
        
    except Exception as e:
        logger.error(f"Error getting enabled features for template: {e}")
        return []

