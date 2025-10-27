"""Роуты владельца для управления инцидентами - использует shared IncidentService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.user import User
from shared.services.incident_service import IncidentService


router = APIRouter()


@router.get("/owner/incidents")
async def owner_incidents_list(
    request: Request,
    status: str = None,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Список инцидентов."""
    from domain.entities.incident import Incident
    
    owner_id = current_user.id
    
    # Получаем инциденты с eager loading
    query = select(Incident).where(Incident.owner_id == owner_id).options(
        selectinload(Incident.object),
        selectinload(Incident.employee),
        selectinload(Incident.shift_schedule),
        selectinload(Incident.creator)
    )
    
    if status:
        query = query.where(Incident.status == status)
    
    query = query.order_by(Incident.created_at.desc()).limit(100)
    result = await session.execute(query)
    incidents = result.scalars().all()
    
    return templates.TemplateResponse(
        "owner/incidents/list.html",
        {
            "request": request, 
            "incidents": incidents,
            "status_filter": status
        }
    )


@router.post("/owner/incidents/create")
async def owner_incidents_create(
    request: Request,
    category: str = Form(...),
    severity: str = Form("medium"),
    object_id: int = Form(None),
    shift_schedule_id: int = Form(None),
    employee_id: int = Form(None),
    notes: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать инцидент вручную."""
    incident_service = IncidentService(session)
    
    await incident_service.create_incident(
        owner_id=current_user.id,
        category=category,
        severity=severity,
        object_id=object_id,
        shift_schedule_id=shift_schedule_id,
        employee_id=employee_id,
        notes=notes,
        created_by=current_user.id
    )
    
    return RedirectResponse(url="/owner/incidents", status_code=303)


@router.post("/owner/incidents/{incident_id}/status")
async def owner_incidents_update_status(
    request: Request,
    incident_id: int,
    new_status: str = Form(...),
    notes: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Изменить статус инцидента."""
    from domain.entities.incident import Incident
    
    incident = await session.get(Incident, incident_id)
    if incident and incident.owner_id == current_user.id:
        incident_service = IncidentService(session)
        await incident_service.update_incident_status(
            incident_id=incident_id,
            new_status=new_status,
            notes=notes
        )
    
    return RedirectResponse(url="/owner/incidents", status_code=303)


@router.post("/owner/incidents/{incident_id}/apply-adjustments")
async def owner_incidents_apply_adjustments(
    request: Request,
    incident_id: int,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Применить предложенные корректировки."""
    from domain.entities.incident import Incident
    
    incident = await session.get(Incident, incident_id)
    if incident and incident.owner_id == current_user.id:
        incident_service = IncidentService(session)
        await incident_service.apply_suggested_adjustments(incident_id)
    
    return RedirectResponse(url="/owner/incidents", status_code=303)
