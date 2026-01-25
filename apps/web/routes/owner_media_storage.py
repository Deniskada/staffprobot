"""Настройки хранилища медиа по владельцу (restruct1 Фаза 1.5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import get_user_id_from_current_user
from core.database.session import get_db_session
from shared.services.owner_media_storage_service import (
    get_all_modes,
    get_context_labels,
    get_storage_mode_labels,
    is_secure_media_enabled,
    set_all_modes,
)

router = APIRouter()


@router.get("/api/options")
async def api_get_options(
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    """GET: { enabled: bool, modes: { tasks: str, ... } }."""
    try:
        user_id = await get_user_id_from_current_user(current_user, db)
        enabled = await is_secure_media_enabled(db, user_id)
        modes = await get_all_modes(db, user_id)
        return JSONResponse({"success": True, "enabled": enabled, "modes": modes})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/options")
async def api_set_options(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    """POST: body { modes: { tasks: "storage", ... } }."""
    try:
        data = await request.json()
        modes = data.get("modes") or {}
        if not isinstance(modes, dict):
            return JSONResponse({"success": False, "error": "modes must be object"}, status_code=400)
        user_id = await get_user_id_from_current_user(current_user, db)
        await set_all_modes(db, user_id, modes)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("", response_class=HTMLResponse)
async def page_media_storage_settings(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    """Страница «Настройки хранилища» (владелец)."""
    request.state.current_user = current_user
    user_id = await get_user_id_from_current_user(current_user, db)
    enabled = await is_secure_media_enabled(db, user_id)
    modes = await get_all_modes(db, user_id)
    context_labels = get_context_labels()
    storage_labels = get_storage_mode_labels()
    return templates.TemplateResponse(
        "owner/profile/media_storage_settings.html",
        {
            "request": request,
            "enabled": enabled,
            "modes": modes,
            "context_labels": context_labels,
            "storage_labels": storage_labels,
        },
    )
