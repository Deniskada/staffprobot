"""
Роуты для управления функциями в профиле владельца.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import get_user_id_from_current_user
from core.database.session import get_db_session
from shared.services.system_features_service import SystemFeaturesService
from core.logging.logger import logger

router = APIRouter()


@router.get("/api/status")
async def get_features_status(
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Получить статус всех функций для пользователя."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        
        service = SystemFeaturesService()
        features_status = await service.get_user_features_status(session, user_id)
        
        # Формируем удобный формат для frontend
        features_list = []
        for key, status in features_status.items():
            feature_info = status['info'].to_dict()
            feature_info['available'] = status['available']
            feature_info['enabled'] = status['enabled']
            features_list.append(feature_info)
        
        # Сортируем по sort_order
        features_list.sort(key=lambda x: x['sort_order'])
        
        return JSONResponse({
            "success": True,
            "features": features_list
        })
    except Exception as e:
        logger.error(f"Error getting features status: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/toggle")
async def toggle_feature(
    feature_key: str,
    enabled: bool,
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Включить/выключить функцию."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        
        service = SystemFeaturesService()
        success = await service.toggle_user_feature(session, user_id, feature_key, enabled)
        
        if not success:
            return JSONResponse({
                "success": False,
                "error": "Функция недоступна в вашем тарифном плане"
            }, status_code=403)
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error toggling feature: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

