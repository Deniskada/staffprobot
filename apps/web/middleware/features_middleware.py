"""
Middleware для автоматического добавления enabled_features в контекст шаблонов.
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from shared.services.system_features_service import SystemFeaturesService
from apps.web.middleware.role_middleware import get_user_id_from_current_user
from core.logging.logger import logger


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

