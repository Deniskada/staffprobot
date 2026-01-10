"""Роуты владельца для управления инцидентами - использует shared IncidentService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload
import io
from datetime import datetime
from typing import List, Dict, Any, Optional

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from core.config.settings import settings
from domain.entities.user import User
from domain.entities.object import Object
from shared.services.incident_service import IncidentService
from shared.services.incident_category_service import IncidentCategoryService
from shared.services.employee_selector_service import EmployeeSelectorService
from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm


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


async def _get_owner_template_context(owner_id: int, session: AsyncSession):
    """Получить контекст для owner шаблонов."""
    from apps.web.routes.owner import get_owner_context
    return await get_owner_context(owner_id, session)


@router.get("/owner/incidents")
async def owner_incidents_list(
    request: Request,
    status: str = Query(None),
    statuses: str = Query(None),  # Множественный фильтр через запятую: "new,in_review"
    category: str = Query(None),
    object_id: int = Query(None),
    employee_id: int = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=10, le=200),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Список инцидентов с пагинацией, сортировкой и множественными фильтрами."""
    if not settings.enable_incidents:
        raise HTTPException(
            status_code=404,
            detail="Incidents отключены. Включите enable_incidents в настройках."
        )
    
    from domain.entities.incident import Incident
    
    owner_id = await _get_db_user_id(current_user, session)
    
    # Базовый запрос
    query = select(Incident).where(Incident.owner_id == owner_id).options(
        selectinload(Incident.object),
        selectinload(Incident.employee),
        selectinload(Incident.shift_schedule),
        selectinload(Incident.creator)
    )
    
    # Множественный фильтр по статусам (приоритет над одиночным фильтром)
    if statuses:
        status_list = [s.strip() for s in statuses.split(",") if s.strip()]
        if status_list:
            query = query.where(Incident.status.in_(status_list))
    elif status:
        # Одиночный фильтр для обратной совместимости
        query = query.where(Incident.status == status)
    
    # Фильтр по категории
    if category:
        query = query.where(Incident.category == category)
    
    # Фильтр по объекту
    if object_id:
        query = query.where(Incident.object_id == object_id)
    
    # Фильтр по сотруднику
    if employee_id:
        query = query.where(Incident.employee_id == employee_id)
    
    # Сортировка
    sort_column_map = {
        "created_at": Incident.created_at,
        "custom_date": Incident.custom_date,
        "category": Incident.category,
        "severity": Incident.severity,
        "status": Incident.status,
        "damage_amount": Incident.damage_amount,
        "number": Incident.custom_number
    }
    sort_column = sort_column_map.get(sort_by, Incident.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # Подсчет общего количества для пагинации (применяем те же фильтры)
    count_query = select(func.count(Incident.id)).where(Incident.owner_id == owner_id)
    
    # Применяем те же фильтры к подсчету
    if statuses:
        status_list = [s.strip() for s in statuses.split(",") if s.strip()]
        if status_list:
            count_query = count_query.where(Incident.status.in_(status_list))
    elif status:
        count_query = count_query.where(Incident.status == status)
    
    if category:
        count_query = count_query.where(Incident.category == category)
    if object_id:
        count_query = count_query.where(Incident.object_id == object_id)
    if employee_id:
        count_query = count_query.where(Incident.employee_id == employee_id)
    
    count_result = await session.execute(count_query)
    total_count = count_result.scalar_one() or 0
    
    # Пагинация
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)
    
    result = await session.execute(query)
    incidents = result.scalars().all()
    
    # Вычисляем параметры пагинации
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

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
    
    # Формируем параметры для сохранения фильтров в URL
    filter_params = {}
    if statuses:
        filter_params["statuses"] = statuses
    elif status:
        filter_params["status"] = status
    if category:
        filter_params["category"] = category
    if object_id:
        filter_params["object_id"] = object_id
    if employee_id:
        filter_params["employee_id"] = employee_id
    if sort_by != "created_at":
        filter_params["sort_by"] = sort_by
    if sort_order != "desc":
        filter_params["sort_order"] = sort_order
    if per_page != 25:
        filter_params["per_page"] = per_page
    
    # Получаем контекст для owner базового шаблона
    owner_context = await _get_owner_template_context(owner_id, session)
    
    return templates.TemplateResponse(
        "owner/incidents/list.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": owner_context.get("available_interfaces", []),
            "new_applications_count": owner_context.get("new_applications_count", 0),
            "incidents": incidents,
            "status_filter": status,
            "statuses_filter": statuses,
            "category_filter": category,
            "object_id_filter": object_id,
            "employee_id_filter": employee_id,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "categories": categories,
            "objects": objects,
            "employees": employees,
            "filter_params": filter_params
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
    owner_context = await _get_owner_template_context(owner_id, session)
    return templates.TemplateResponse(
        "owner/incidents/create.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": owner_context.get("available_interfaces", []),
            "new_applications_count": owner_context.get("new_applications_count", 0),
            "categories": categories,
            "objects": objects
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
    return_url: str = Query(None),
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
        changed_by_id = owner_db_id
        await incident_service.update_incident_status(
            incident_id=incident_id,
            new_status=new_status,
            notes=notes,
            changed_by=changed_by_id
        )
    
    # Возвращаемся на указанную страницу или на список с фильтром
    if return_url:
        return RedirectResponse(url=return_url, status_code=303)
    
    status_param = f"?status={new_status}" if new_status else ""
    return RedirectResponse(url=f"/owner/incidents{status_param}", status_code=303)


@router.get("/owner/incidents/{incident_id}/edit")
async def owner_incident_edit_page(
    request: Request,
    incident_id: int,
    return_url: str = Query(None),
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
    employee_groups = {"active": [], "former": []}
    if incident.object_id:
        selector = EmployeeSelectorService(session)
        employee_groups = await selector.get_employees_for_owner(owner_db_id, object_id=incident.object_id)
    adjustments = await IncidentService(session).get_adjustments_by_incident(incident.id)
    
    # Формируем URL возврата к списку
    back_url = return_url or "/owner/incidents"
    
    # Получаем контекст для owner базового шаблона
    owner_context = await _get_owner_template_context(owner_db_id, session)
    
    return templates.TemplateResponse(
        "owner/incidents/edit.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": owner_context.get("available_interfaces", []),
            "new_applications_count": owner_context.get("new_applications_count", 0),
            "incident": incident,
            "categories": categories,
            "history": history,
            "objects": objects,
            "employee_groups": employee_groups,
            "adjustments": adjustments,
            "back_url": back_url,
        }
    )


@router.get("/owner/incidents/api/employees", response_class=JSONResponse)
async def owner_incident_employees(
    object_id: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session),
):
    """Вернуть сотрудников (активных и уволенных) для выбранного объекта."""
    owner_id = await _get_db_user_id(current_user, session)
    if not owner_id:
        raise HTTPException(status_code=403, detail="Пользователь не найден")

    selector = EmployeeSelectorService(session)
    obj = await session.get(Object, object_id)
    if not obj or obj.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Объект не найден")

    grouped = await selector.get_employees_for_owner(owner_id, object_id=object_id)
    return JSONResponse(grouped)


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
    return_url: str = Form(None),
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
    owner_db_id = await _get_db_user_id(current_user, session)
    if not incident or incident.owner_id != owner_db_id:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    
    # Проверка статуса: решенные, отклоненные и отмененные инциденты нельзя редактировать
    if incident.status in ['resolved', 'rejected', 'cancelled']:
        raise HTTPException(status_code=400, detail=f"Нельзя редактировать инцидент со статусом '{incident.status}'")
    
    service = IncidentService(session)
    changed_by_id = owner_db_id
    
    # Если статус изменился — применяем через IncidentService для истории
    if status and status != incident.status:
        if status not in ["new", "in_review", "resolved", "rejected", "cancelled"]:
            raise HTTPException(status_code=400, detail="Некорректный статус")
        await service.update_incident_status(
            incident_id=incident_id,
            new_status=status,
            notes=None,
            changed_by=changed_by_id
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
        await service.update_incident(incident_id, data, changed_by_id)
    except ValueError as e:
        # Ошибка при попытке редактировать resolved/rejected инцидент
        raise HTTPException(status_code=400, detail=str(e))
    
    # Возвращаемся на указанную страницу или на список
    if return_url:
        return RedirectResponse(url=return_url, status_code=303)
    
    return RedirectResponse(url="/owner/incidents", status_code=303)


@router.get("/owner/incidents/categories")
async def owner_incident_categories(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    owner_id = await _get_db_user_id(current_user, session)
    cats = await IncidentCategoryService(session).list_categories(owner_id)
    owner_context = await _get_owner_template_context(owner_id, session)
    return templates.TemplateResponse(
        "owner/incidents/categories.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": owner_context.get("available_interfaces", []),
            "new_applications_count": owner_context.get("new_applications_count", 0),
            "categories": cats
        }
    )


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
    owner_id = await _get_db_user_id(current_user, session)
    owner_context = await _get_owner_template_context(owner_id, session)
    return templates.TemplateResponse(
        "owner/incidents/reports.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": owner_context.get("available_interfaces", []),
            "new_applications_count": owner_context.get("new_applications_count", 0)
        }
    )


@router.post("/owner/incidents/{incident_id}/cancel")
async def owner_incidents_cancel(
    request: Request,
    incident_id: int,
    cancellation_reason: str = Form(...),
    notes: str = Form(None),
    return_url: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Отменить инцидент с указанием причины."""
    from domain.entities.incident import Incident
    from fastapi import HTTPException
    
    owner_db_id = await _get_db_user_id(current_user, session)
    incident = await session.get(Incident, incident_id)
    if not incident or incident.owner_id != owner_db_id:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    
    incident_service = IncidentService(session)
    cancelled_by_id = owner_db_id
    
    try:
        await incident_service.cancel_incident(
            incident_id=incident_id,
            cancellation_reason=cancellation_reason,
            cancelled_by=cancelled_by_id,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from core.logging.logger import logger
        logger.error("Error cancelling incident", incident_id=incident_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при отмене инцидента: {str(e)}")
    
    # Возвращаемся на указанную страницу или на список
    if return_url:
        return RedirectResponse(url=return_url, status_code=303)
    
    return RedirectResponse(url="/owner/incidents?statuses=cancelled", status_code=303)


@router.post("/owner/incidents/{incident_id}/apply-adjustments")
async def owner_incidents_apply_adjustments(
    request: Request,
    incident_id: int,
    return_url: str = Query(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Применить предложенные корректировки."""
    from domain.entities.incident import Incident
    
    owner_db_id = await _get_db_user_id(current_user, session)
    incident = await session.get(Incident, incident_id)
    if incident and incident.owner_id == owner_db_id:
        incident_service = IncidentService(session)
        await incident_service.apply_suggested_adjustments(incident_id)
    
    # Возвращаемся на указанную страницу или на список
    if return_url:
        return RedirectResponse(url=return_url, status_code=303)
    
    return RedirectResponse(url="/owner/incidents", status_code=303)


async def _get_filtered_incidents_for_export(
    session: AsyncSession,
    owner_id: int,
    status: Optional[str] = None,
    statuses: Optional[str] = None,
    category: Optional[str] = None,
    object_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> List:
    """Получить отфильтрованные инциденты для экспорта (без пагинации)."""
    from domain.entities.incident import Incident
    
    query = select(Incident).where(Incident.owner_id == owner_id).options(
        selectinload(Incident.object),
        selectinload(Incident.employee),
        selectinload(Incident.shift_schedule),
        selectinload(Incident.creator)
    )
    
    # Множественный фильтр по статусам
    if statuses:
        status_list = [s.strip() for s in statuses.split(",") if s.strip()]
        if status_list:
            query = query.where(Incident.status.in_(status_list))
    elif status:
        query = query.where(Incident.status == status)
    
    # Фильтр по категории
    if category:
        query = query.where(Incident.category == category)
    
    # Фильтр по объекту
    if object_id:
        query = query.where(Incident.object_id == object_id)
    
    # Фильтр по сотруднику
    if employee_id:
        query = query.where(Incident.employee_id == employee_id)
    
    # Сортировка
    sort_column_map = {
        "created_at": Incident.created_at,
        "custom_date": Incident.custom_date,
        "category": Incident.category,
        "severity": Incident.severity,
        "status": Incident.status,
        "damage_amount": Incident.damage_amount,
        "number": Incident.custom_number
    }
    sort_column = sort_column_map.get(sort_by, Incident.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    result = await session.execute(query)
    return result.scalars().all()


def _get_category_display_export(category: str) -> str:
    """Получить отображаемое название категории для экспорта."""
    category_map = {
        "late_arrival": "Опоздание",
        "task_non_completion": "Невыполнение задачи",
        "damage": "Повреждение",
        "violation": "Нарушение"
    }
    return category_map.get(category, category)


def _get_severity_display_export(severity: Optional[str]) -> str:
    """Получить отображаемое название критичности для экспорта."""
    if not severity:
        return "Средняя"
    severity_map = {
        "low": "Низкая",
        "medium": "Средняя",
        "high": "Высокая",
        "critical": "Критично"
    }
    return severity_map.get(severity, severity)


def _get_status_display_export(status: str) -> str:
    """Получить отображаемое название статуса для экспорта."""
    status_map = {
        "new": "Новый",
        "in_review": "На рассмотрении",
        "resolved": "Решён",
        "rejected": "Отклонён",
        "cancelled": "Отменён"
    }
    return status_map.get(status, status)


@router.get("/owner/incidents/export/excel")
async def owner_incidents_export_excel(
    request: Request,
    status: str = Query(None),
    statuses: str = Query(None),
    category: str = Query(None),
    object_id: int = Query(None),
    employee_id: int = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Экспорт инцидентов в Excel."""
    if not settings.enable_incidents:
        raise HTTPException(status_code=404, detail="Incidents отключены")
    
    owner_id = await _get_db_user_id(current_user, session)
    incidents = await _get_filtered_incidents_for_export(
        session, owner_id, status, statuses, category, object_id, employee_id, sort_by, sort_order
    )
    
    # Подготовка данных для Excel
    data = []
    for inc in incidents:
        data.append({
            "Номер": inc.custom_number or f"#{inc.id}",
            "Дата": inc.custom_date.strftime('%d.%m.%Y') if inc.custom_date else inc.created_at.strftime('%d.%m.%Y'),
            "Категория": _get_category_display_export(inc.category),
            "Критичность": _get_severity_display_export(inc.severity),
            "Статус": _get_status_display_export(inc.status),
            "Объект": inc.object.name if inc.object else "—",
            "Сотрудник": f"{inc.employee.last_name} {inc.employee.first_name}".strip() if inc.employee else "—",
            "Ущерб, ₽": f"{inc.damage_amount:,.2f}".replace(',', ' ') if inc.damage_amount else "—",
            "Создал": inc.creator.first_name if inc.creator else "—",
            "Создан": inc.created_at.strftime('%d.%m.%Y %H:%M'),
            "Примечания": (inc.notes or "")[:100] + "..." if inc.notes and len(inc.notes) > 100 else (inc.notes or "—")
        })
    
    if not data:
        raise HTTPException(status_code=404, detail="Нет данных для экспорта")
    
    # Создание Excel файла
    df = pd.DataFrame(data)
    wb = Workbook()
    ws = wb.active
    ws.title = "Инциденты"
    
    # Добавление данных
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    
    # Стилизация
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Автоширина колонок
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Сохранение в память
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"incidents_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
    )


@router.get("/owner/incidents/export/pdf")
async def owner_incidents_export_pdf(
    request: Request,
    status: str = Query(None),
    statuses: str = Query(None),
    category: str = Query(None),
    object_id: int = Query(None),
    employee_id: int = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Экспорт инцидентов в PDF."""
    if not settings.enable_incidents:
        raise HTTPException(status_code=404, detail="Incidents отключены")
    
    owner_id = await _get_db_user_id(current_user, session)
    incidents = await _get_filtered_incidents_for_export(
        session, owner_id, status, statuses, category, object_id, employee_id, sort_by, sort_order
    )
    
    if not incidents:
        raise HTTPException(status_code=404, detail="Нет данных для экспорта")
    
    # Создание PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Определяем доступный шрифт
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
            font_name = 'DejaVuSans'
        else:
            font_name = 'Helvetica'
    except:
        font_name = 'Helvetica'
    
    # Стили
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1,  # Центрирование
        fontName=font_name
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName=font_name
    )
    
    story = []
    
    # Заголовок
    story.append(Paragraph("Отчет по инцидентам", title_style))
    story.append(Spacer(1, 12))
    
    # Информация о фильтрах
    filter_info = []
    if statuses:
        filter_info.append(f"Статусы: {statuses}")
    elif status:
        filter_info.append(f"Статус: {status}")
    if category:
        filter_info.append(f"Категория: {category}")
    if object_id:
        obj = await session.get(Object, object_id)
        if obj:
            filter_info.append(f"Объект: {obj.name}")
    if employee_id:
        from domain.entities.user import User as UserEntity
        emp = await session.get(UserEntity, employee_id)
        if emp:
            filter_info.append(f"Сотрудник: {emp.last_name} {emp.first_name}")
    
    if filter_info:
        story.append(Paragraph("Фильтры: " + ", ".join(filter_info), normal_style))
        story.append(Spacer(1, 12))
    
    story.append(Paragraph(f"Всего инцидентов: {len(incidents)}", normal_style))
    story.append(Spacer(1, 12))
    
    # Таблица инцидентов
    table_data = [["Номер", "Дата", "Категория", "Критичность", "Статус", "Объект", "Сотрудник", "Ущерб"]]
    
    for inc in incidents:
        table_data.append([
            inc.custom_number or f"#{inc.id}",
            (inc.custom_date.strftime('%d.%m.%Y') if inc.custom_date else inc.created_at.strftime('%d.%m.%Y'))[:10],
            _get_category_display_export(inc.category)[:15],
            _get_severity_display_export(inc.severity)[:10],
            _get_status_display_export(inc.status)[:15],
            (inc.object.name if inc.object else "—")[:20],
            (f"{inc.employee.last_name} {inc.employee.first_name}".strip() if inc.employee else "—")[:20],
            f"{inc.damage_amount:,.2f}".replace(',', ' ') if inc.damage_amount else "—"
        ])
    
    table = Table(table_data, colWidths=[2*cm, 2*cm, 2.5*cm, 2*cm, 2.5*cm, 3*cm, 3*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(table)
    
    # Генерация PDF
    doc.build(story)
    buffer.seek(0)
    
    filename = f"incidents_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
    )
