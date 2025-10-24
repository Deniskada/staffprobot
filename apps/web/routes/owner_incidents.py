"""Роуты владельца для управления инцидентами."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.incident import Incident
from domain.entities.user import User


router = APIRouter()


@router.get("/owner/incidents")
async def owner_incidents_list(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Список инцидентов."""
    owner_id = current_user.id
    query = select(Incident).where(Incident.owner_id == owner_id).order_by(Incident.created_at.desc()).limit(50)
    result = await session.execute(query)
    incidents = result.scalars().all()
    return templates.TemplateResponse(
        "owner/incidents/list.html",
        {"request": request, "incidents": incidents}
    )

