"""Роуты сотрудника для работы с тикетами (обращения)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.database.session import get_db_session
from domain.entities.user import User
from domain.entities.contract import Contract
from domain.entities.incident import Incident
from domain.entities.object import Object
from shared.services.incident_service import IncidentService
from shared.services.incident_category_service import IncidentCategoryService
from shared.services.incident_item_service import IncidentItemService
from shared.services.product_service import ProductService

router = APIRouter()


async def _get_employee_user_id(current_user, session: AsyncSession) -> int:
    """Получить внутренний user_id сотрудника."""
    from apps.web.middleware.role_middleware import get_user_id_from_current_user
    user_id = await get_user_id_from_current_user(current_user, session)
    if user_id is None:
        raise HTTPException(status_code=403, detail="Пользователь не найден")
    return user_id


async def _get_employee_owner_ids(user_id: int, session: AsyncSession) -> list[int]:
    """Получить список owner_id по активным контрактам сотрудника."""
    result = await session.execute(
        select(Contract.owner_id).where(
            Contract.employee_id == user_id,
            Contract.is_active == True,
        ).distinct()
    )
    return [row[0] for row in result.all()]


async def _get_employee_context(current_user, session: AsyncSession) -> dict:
    """Базовый контекст для шаблонов сотрудника."""
    from apps.web.routes.employee import get_available_interfaces_for_user
    try:
        available_interfaces = await get_available_interfaces_for_user(current_user, session)
        return {"available_interfaces": available_interfaces, "applications_count": 0}
    except Exception:
        return {"available_interfaces": [], "applications_count": 0}


@router.get("/employee/incidents")
async def employee_incidents_list(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user_dependency()),
    _=Depends(require_employee_or_applicant),
    session: AsyncSession = Depends(get_db_session),
):
    """Список тикетов сотрудника (все типы, свои)."""
    user_id = await _get_employee_user_id(current_user, session)

    query = select(Incident).where(
        Incident.employee_id == user_id
    ).options(
        selectinload(Incident.object),
        selectinload(Incident.creator),
    ).order_by(Incident.created_at.desc())

    if status:
        query = query.where(Incident.status == status)

    result = await session.execute(query)
    incidents = result.scalars().all()

    base_ctx = await _get_employee_context(current_user, session)

    return templates.TemplateResponse(
        "employee/incidents/list.html",
        {
            "request": request,
            "current_user": current_user,
            **base_ctx,
            "incidents": incidents,
            "status_filter": status,
        },
    )


@router.get("/employee/incidents/create")
async def employee_incident_create_page(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _=Depends(require_employee_or_applicant),
    session: AsyncSession = Depends(get_db_session),
):
    """Форма создания обращения (только тип request)."""
    user_id = await _get_employee_user_id(current_user, session)
    owner_ids = await _get_employee_owner_ids(user_id, session)
    if not owner_ids:
        raise HTTPException(status_code=403, detail="Нет активных контрактов")

    owner_id = owner_ids[0]
    categories = await IncidentCategoryService(session).list_categories(owner_id, incident_type="request")
    products_raw = await ProductService(session).list_products(owner_id)
    products = [
        {"id": p.id, "name": p.name, "unit": p.unit, "price": float(p.price)}
        for p in products_raw
    ]
    obj_result = await session.execute(
        select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name)
    )
    objects = obj_result.scalars().all()
    base_ctx = await _get_employee_context(current_user, session)
    return templates.TemplateResponse(
        "employee/incidents/create.html",
        {
            "request": request,
            "current_user": current_user,
            **base_ctx,
            "categories": categories,
            "products": products,
            "objects": objects,
            "owner_id": owner_id,
        },
    )


@router.post("/employee/incidents/create")
async def employee_incident_create_save(
    request: Request,
    category: str = Form(...),
    notes: str = Form(None),
    object_id: int = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _=Depends(require_employee_or_applicant),
    session: AsyncSession = Depends(get_db_session),
):
    """Создать обращение (только тип request)."""
    user_id = await _get_employee_user_id(current_user, session)
    owner_ids = await _get_employee_owner_ids(user_id, session)
    if not owner_ids:
        raise HTTPException(status_code=403, detail="Нет активных контрактов")

    owner_id = owner_ids[0]
    incident_service = IncidentService(session)
    incident = await incident_service.create_incident(
        owner_id=owner_id,
        incident_type="request",
        category=category,
        severity="low",
        object_id=object_id if object_id else None,
        employee_id=user_id,
        notes=notes,
        created_by=user_id,
    )
    form_data = await request.form()
    item_service = IncidentItemService(session)
    idx = 0
    while True:
        pid_key = f"items[{idx}][product_id]"
        if pid_key not in form_data:
            break
        try:
            product_id = int(form_data[pid_key]) if form_data[pid_key] else None
            product_name = form_data.get(f"items[{idx}][product_name]", "")
            quantity = float(form_data.get(f"items[{idx}][quantity]", 1))
            price = float(form_data.get(f"items[{idx}][price]", 0))
            if product_name and quantity > 0:
                await item_service.add_item(
                    incident_id=incident.id,
                    product_id=product_id,
                    product_name=product_name,
                    quantity=quantity,
                    price=price,
                    added_by=user_id,
                )
        except (ValueError, TypeError):
            pass
        idx += 1
    return RedirectResponse(url="/employee/incidents", status_code=303)


@router.get("/employee/incidents/{incident_id}")
async def employee_incident_detail(
    request: Request,
    incident_id: int,
    current_user: User = Depends(get_current_user_dependency()),
    _=Depends(require_employee_or_applicant),
    session: AsyncSession = Depends(get_db_session),
):
    """Просмотр тикета сотрудником (с историей изменений)."""
    user_id = await _get_employee_user_id(current_user, session)

    result = await session.execute(
        select(Incident).options(
            selectinload(Incident.object),
            selectinload(Incident.employee),
            selectinload(Incident.creator),
        ).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident or incident.employee_id != user_id:
        raise HTTPException(status_code=404, detail="Тикет не найден")

    # История
    from domain.entities.incident_history import IncidentHistory
    hist_res = await session.execute(
        select(IncidentHistory)
        .options(selectinload(IncidentHistory.changer))
        .where(IncidentHistory.incident_id == incident.id)
        .order_by(IncidentHistory.changed_at.desc())
    )
    history = hist_res.scalars().all()

    # Позиции
    items = await IncidentItemService(session).list_items(incident.id)

    base_ctx = await _get_employee_context(current_user, session)
    can_edit = (
        incident.incident_type == "request"
        and incident.status == "new"
    )

    return templates.TemplateResponse(
        "employee/incidents/detail.html",
        {
            "request": request,
            "current_user": current_user,
            **base_ctx,
            "incident": incident,
            "history": history,
            "incident_items": items,
            "can_edit": can_edit,
        },
    )


def _employee_can_edit_incident(incident: Incident, user_id: int) -> bool:
    """Сотрудник может редактировать только своё обращение в статусе «новый»."""
    return (
        incident.employee_id == user_id
        and incident.incident_type == "request"
        and incident.status == "new"
    )


@router.get("/employee/incidents/{incident_id}/edit")
async def employee_incident_edit_page(
    request: Request,
    incident_id: int,
    current_user: User = Depends(get_current_user_dependency()),
    _=Depends(require_employee_or_applicant),
    session: AsyncSession = Depends(get_db_session),
):
    """Форма редактирования обращения (только своё, только статус «новый»)."""
    user_id = await _get_employee_user_id(current_user, session)
    result = await session.execute(
        select(Incident).options(
            selectinload(Incident.object),
        ).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident or not _employee_can_edit_incident(incident, user_id):
        raise HTTPException(status_code=404, detail="Тикет не найден или редактирование недоступно")

    owner_id = incident.owner_id
    categories = await IncidentCategoryService(session).list_categories(owner_id, incident_type="request")
    products_raw = await ProductService(session).list_products(owner_id)
    products = [
        {"id": p.id, "name": p.name, "unit": p.unit, "price": float(p.price)}
        for p in products_raw
    ]
    obj_result = await session.execute(
        select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name)
    )
    objects = obj_result.scalars().all()
    items = await IncidentItemService(session).list_items(incident.id)
    incident_items_json = [
        {
            "product_id": it.product_id,
            "product_name": it.product_name or "",
            "quantity": float(it.quantity or 0),
            "price": float(it.price or 0),
        }
        for it in items
    ]
    base_ctx = await _get_employee_context(current_user, session)
    return templates.TemplateResponse(
        "employee/incidents/edit.html",
        {
            "request": request,
            "current_user": current_user,
            **base_ctx,
            "incident": incident,
            "categories": categories,
            "products": products,
            "objects": objects,
            "incident_items": incident_items_json,
        },
    )


@router.post("/employee/incidents/{incident_id}/edit")
async def employee_incident_edit_save(
    request: Request,
    incident_id: int,
    category: str = Form(...),
    notes: str = Form(None),
    object_id: int = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _=Depends(require_employee_or_applicant),
    session: AsyncSession = Depends(get_db_session),
):
    """Сохранить изменения обращения (только своё, только статус «новый»)."""
    user_id = await _get_employee_user_id(current_user, session)
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident or not _employee_can_edit_incident(incident, user_id):
        raise HTTPException(status_code=404, detail="Тикет не найден или редактирование недоступно")

    incident_service = IncidentService(session)
    await incident_service.update_incident(
        incident_id=incident_id,
        data={
            "category": category,
            "notes": notes or "",
            "object_id": object_id if object_id else None,
        },
        changed_by=user_id,
    )

    item_service = IncidentItemService(session)
    existing = await item_service.list_items(incident_id)
    for it in existing:
        await item_service.remove_item(it.id, removed_by=user_id)

    form_data = await request.form()
    idx = 0
    while True:
        pid_key = f"items[{idx}][product_id]"
        if pid_key not in form_data:
            break
        try:
            product_id = int(form_data[pid_key]) if form_data[pid_key] else None
            product_name = form_data.get(f"items[{idx}][product_name]", "")
            quantity = float(form_data.get(f"items[{idx}][quantity]", 1))
            price = float(form_data.get(f"items[{idx}][price]", 0))
            if product_name and quantity > 0:
                await item_service.add_item(
                    incident_id=incident_id,
                    product_id=product_id,
                    product_name=product_name,
                    quantity=quantity,
                    price=price,
                    added_by=user_id,
                )
        except (ValueError, TypeError):
            pass
        idx += 1

    return RedirectResponse(url=f"/employee/incidents/{incident_id}", status_code=303)
