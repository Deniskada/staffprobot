"""
Роуты для управления профилями организаций.
"""

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from apps.web.dependencies import get_current_user, require_owner_or_superadmin, get_db_session
from shared.services.organization_profile_service import OrganizationProfileService
from shared.services.user_service import get_user_id_from_current_user
from core.logging.logger import logger

router = APIRouter()


@router.get("/api/list")
async def list_organization_profiles(
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Получить список профилей организаций пользователя."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        
        service = OrganizationProfileService()
        profiles = await service.list_user_profiles(session, user_id)
        
        return JSONResponse({
            "success": True,
            "profiles": [p.to_dict() for p in profiles]
        })
    except Exception as e:
        logger.error(f"Error listing organization profiles: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/create")
async def create_organization_profile(
    profile_name: str = Form(...),
    legal_type: str = Form(...),
    is_default: bool = Form(False),
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать профиль организации."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        
        # Получаем реквизиты из формы
        # TODO: parse requisites from form data
        requisites = {}
        
        service = OrganizationProfileService()
        profile = await service.create_profile(
            session,
            user_id,
            profile_name,
            legal_type,
            requisites,
            is_default
        )
        
        return JSONResponse({
            "success": True,
            "profile": profile.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating organization profile: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/{profile_id}/update")
async def update_organization_profile(
    profile_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Обновить профиль организации."""
    try:
        # TODO: parse form data
        data = {}
        
        service = OrganizationProfileService()
        profile = await service.update_profile(session, profile_id, data)
        
        if not profile:
            return JSONResponse({"success": False, "error": "Profile not found"}, status_code=404)
        
        return JSONResponse({
            "success": True,
            "profile": profile.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating organization profile: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.delete("/api/{profile_id}")
async def delete_organization_profile(
    profile_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Удалить профиль организации."""
    try:
        service = OrganizationProfileService()
        success = await service.delete_profile(session, profile_id)
        
        if not success:
            return JSONResponse({"success": False, "error": "Profile not found"}, status_code=404)
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error deleting organization profile: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/{profile_id}/set-default")
async def set_default_organization_profile(
    profile_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Установить профиль как профиль по умолчанию."""
    try:
        service = OrganizationProfileService()
        success = await service.set_default_profile(session, profile_id)
        
        if not success:
            return JSONResponse({"success": False, "error": "Profile not found"}, status_code=404)
        
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error setting default profile: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

