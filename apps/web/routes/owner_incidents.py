"""Роуты владельца для управления инцидентами - использует shared IncidentService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from core.config.settings import settings
from domain.entities.user import User
from shared.services.incident_service import IncidentService
from shared.services.incident_category_service import IncidentCategoryService
from fastapi import HTTPException


router = APIRouter()


async def _get_db_user_id(current_user, session: AsyncSession) -> int | None:
    """Локальный helper: получить внутренний user_id по current_user (JWT словарь или ORM User)."""
    from sqlalchemy import select as sql_select
    from domain.entities.user import User as UserEntity
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        res = await session.execute(sql_select(UserEntity).where(UserEntity.telegram_id == telegram_id))
        u = res.scalar_one_or_none()
        return u.id if u else None
    return current_user.id

@router.get("/owner/incidents")
async def owner_incidents_list(
    request: Request,
    status: str = None,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Список инцидентов."""
    if not settings.enable_incidents:
        raise HTTPException(
            status_code=404,
            detail="Incidents отключены. Включите enable_incidents в настройках."
        )
    
    from domain.entities.incident import Incident
    
    owner_id = await _get_db_user_id(current_user, session)
    
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

    # Категории владельца
    categories = await IncidentCategoryService(session).list_categories(owner_id)

    # Объекты владельца
    from domain.entities.object import Object
    obj_res = await session.execute(select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name))
    objects = obj_res.scalars().all()

    # Сотрудники владельца по активным договорам (не менеджеры)
    from domain.entities.contract import Contract
    emp_ids_res = await session.execute(
        select(Contract.employee_id)
        .where(
            Contract.owner_id == owner_id,
            Contract.is_active == True
        )
        .distinct()
    )
    employee_ids = [row[0] for row in emp_ids_res.all()]
    from domain.entities.user import User as UserEntity
    employees = []
    if employee_ids:
        emp_res = await session.execute(
            select(UserEntity)
            .where(UserEntity.id.in_(employee_ids))
            .order_by(UserEntity.last_name, UserEntity.first_name)
        )
        employees = emp_res.scalars().all()
    
    return templates.TemplateResponse(
        "owner/incidents/list.html",
        {
            "request": request, 
            "incidents": incidents,
            "status_filter": status,
            "categories": categories,
            "objects": objects,
            "employees": employees
        }
    )
@router.get("/owner/incidents/create")
async def owner_incident_create_page(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    owner_id = await _get_db_user_id(current_user, session)
    categories = await IncidentCategoryService(session).list_categories(owner_id)
    from domain.entities.object import Object
    obj_res = await session.execute(select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name))
    objects = obj_res.scalars().all()
    from domain.entities.contract import Contract
    emp_ids_res = await session.execute(
        select(Contract.employee_id)
        .where(
            Contract.owner_id == owner_id,
            Contract.is_active == True
        )
        .distinct()
    )
    employee_ids = [row[0] for row in emp_ids_res.all()]
    from domain.entities.user import User as UserEntity
    employees = []
    if employee_ids:
        emp_res = await session.execute(
            select(UserEntity)
            .where(UserEntity.id.in_(employee_ids))
            .order_by(UserEntity.last_name, UserEntity.first_name)
        )
        employees = emp_res.scalars().all()
    return templates.TemplateResponse(
        "owner/incidents/create.html",
        {"request": request, "categories": categories, "objects": objects, "employees": employees}
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
    custom_number: str = Form(None),
    custom_date: str = Form(None),
    damage_amount: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать инцидент вручную."""
    incident_service = IncidentService(session)
    from datetime import datetime
    from decimal import Decimal
    parsed_date = None
    if custom_date:
        try:
            parsed_date = datetime.strptime(custom_date, "%Y-%m-%d").date()
        except Exception:
            parsed_date = None
    parsed_damage = None
    if damage_amount:
        try:
            parsed_damage = Decimal(damage_amount)
        except Exception:
            parsed_damage = None

    owner_db_id = await _get_db_user_id(current_user, session)
    await incident_service.create_incident(
        owner_id=owner_db_id,
        category=category,
        severity=severity,
        object_id=object_id,
        shift_schedule_id=shift_schedule_id,
        employee_id=employee_id,
        notes=notes,
        created_by=current_user.id,
        custom_number=custom_number,
        custom_date=parsed_date,
        damage_amount=parsed_damage
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
    
    owner_db_id = await _get_db_user_id(current_user, session)
    incident = await session.get(Incident, incident_id)
    if incident and incident.owner_id == owner_db_id:
        incident_service = IncidentService(session)
        await incident_service.update_incident_status(
            incident_id=incident_id,
            new_status=new_status,
            notes=notes
        )
    
    return RedirectResponse(url="/owner/incidents", status_code=303)


@router.get("/owner/incidents/{incident_id}/edit")
async def owner_incident_edit_page(
    request: Request,
    incident_id: int,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    from domain.entities.incident import Incident
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    # Eager load basic relations
    result = await session.execute(
        select(Incident)
        .options(
            selectinload(Incident.object),
            selectinload(Incident.employee)
        )
        .where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    owner_db_id = await _get_db_user_id(current_user, session)
    if not incident or incident.owner_id != owner_db_id:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    # История изменений
    from domain.entities.incident_history import IncidentHistory
    hist_res = await session.execute(
        select(IncidentHistory)
        .options(selectinload(IncidentHistory.changer))
        .where(IncidentHistory.incident_id == incident.id)
        .order_by(IncidentHistory.changed_at.desc())
    )
    history = hist_res.scalars().all()
    categories = await IncidentCategoryService(session).list_categories(owner_db_id)
    # Списки объектов и сотрудников владельца
    from domain.entities.object import Object
    obj_res = await session.execute(select(Object).where(Object.owner_id == owner_db_id, Object.is_active == True).order_by(Object.name))
    objects = obj_res.scalars().all()
    from domain.entities.contract import Contract
    emp_ids_res = await session.execute(
        select(Contract.employee_id)
        .where(
            Contract.owner_id == owner_db_id,
            Contract.is_active == True
        )
        .distinct()
    )
    employee_ids = [row[0] for row in emp_ids_res.all()]
    from domain.entities.user import User as UserEntity
    employees = []
    if employee_ids:
        emp_res = await session.execute(
            select(UserEntity)
            .where(UserEntity.id.in_(employee_ids))
            .order_by(UserEntity.last_name, UserEntity.first_name)
        )
        employees = emp_res.scalars().all()
    return templates.TemplateResponse(
        "owner/incidents/edit.html",
        {"request": request, "incident": incident, "categories": categories, "history": history, "objects": objects, "employees": employees}
    )


@router.post("/owner/incidents/{incident_id}/edit")
async def owner_incident_edit_save(
    request: Request,
    incident_id: int,
    category: str = Form(None),
    severity: str = Form(None),
    object_id: int = Form(None),
    shift_schedule_id: int = Form(None),
    employee_id: int = Form(None),
    notes: str = Form(None),
    custom_number: str = Form(None),
    custom_date: str = Form(None),
    damage_amount: str = Form(None),
    status: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    from decimal import Decimal
    from datetime import datetime
    from domain.entities.incident import Incident
    from sqlalchemy import select
    from fastapi import HTTPException
    
    # Проверяем статус инцидента перед редактированием
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    
    # Проверка статуса: решенные и отклоненные инциденты нельзя редактировать
    if incident.status in ['resolved', 'rejected']:
        raise HTTPException(status_code=400, detail=f"Нельзя редактировать инцидент со статусом '{incident.status}'")
    
    service = IncidentService(session)
    
    # Если статус изменился — применяем через IncidentService для истории
    if status and status != incident.status:
        if status not in ["new", "in_review", "resolved", "rejected"]:
            raise HTTPException(status_code=400, detail="Некорректный статус")
        await service.update_incident_status(
            incident_id=incident_id,
            new_status=status,
            notes=None
        )
        await session.commit()
        # После изменения статуса нужно обновить инцидент из БД
        await session.refresh(incident)
    
    data = {
        k: v for k, v in {
            "category": category,
            "severity": severity,
            "object_id": object_id,
            "shift_schedule_id": shift_schedule_id,
            "employee_id": employee_id,
            "notes": notes,
            "custom_number": custom_number
        }.items() if v is not None and v != ""
    }
    if custom_date:
        try:
            data["custom_date"] = datetime.strptime(custom_date, "%Y-%m-%d").date()
        except Exception:
            pass
    if damage_amount:
        try:
            data["damage_amount"] = Decimal(damage_amount)
        except Exception:
            pass
    
    try:
        await service.update_incident(incident_id, data, current_user.id)
    except ValueError as e:
        # Ошибка при попытке редактировать resolved/rejected инцидент
        raise HTTPException(status_code=400, detail=str(e))
    
    return RedirectResponse(url="/owner/incidents", status_code=303)


@router.get("/owner/incidents/categories")
async def owner_incident_categories(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    cats = await IncidentCategoryService(session).list_categories(current_user.id)
    return templates.TemplateResponse("owner/incidents/categories.html", {"request": request, "categories": cats})


@router.post("/owner/incidents/categories")
async def owner_incident_categories_save(
    request: Request,
    name: str = Form(...),
    category_id: int = Form(None),
    action: str = Form("save"),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    svc = IncidentCategoryService(session)
    if action == "deactivate" and category_id:
        await svc.deactivate(category_id)
    else:
        await svc.create_or_update(current_user.id, name=name, category_id=category_id)
    return RedirectResponse(url="/owner/incidents/categories", status_code=303)


@router.get("/owner/incidents/reports")
async def owner_incidents_reports_page(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    return templates.TemplateResponse("owner/incidents/reports.html", {"request": request})


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
