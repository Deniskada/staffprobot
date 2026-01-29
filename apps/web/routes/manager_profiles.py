"""Роуты мастера профилей для управляющего."""

from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.dependencies import get_current_user_dependency
from apps.web.middleware.role_middleware import require_manager_or_owner, get_user_id_from_current_user
from core.database.session import get_db_session
from apps.web.jinja import templates
from shared.services.role_based_login_service import RoleService, RoleService as _  # for potential future use
import os

router = APIRouter()


@router.get("/profiles", response_class=HTMLResponse)
async def manager_profiles_page(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Страница мастера «Мои профили» для управляющего."""
    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    from .manager import get_manager_context

    context = await get_manager_context(user_id, db)
    selected_profile_id: Optional[str] = request.query_params.get("profile_id")

    yandex_maps_api_key = os.getenv("YANDEX_MAPS_API_KEY", "")

    return templates.TemplateResponse(
        "manager/profile/profiles.html",
        {
            "request": request,
            "current_user": current_user,
            "selected_profile_id": selected_profile_id,
            "yandex_maps_api_key": yandex_maps_api_key,
            **context,
        },
    )

