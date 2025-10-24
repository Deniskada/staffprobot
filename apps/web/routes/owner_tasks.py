"""Роуты владельца для управления задачами (Tasks v2) - использует shared TaskService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.user import User
from shared.services.task_service import TaskService


router = APIRouter()


@router.get("/owner/tasks")
async def owner_tasks_index(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Главная страница задач."""
    return templates.TemplateResponse(
        "owner/tasks/index.html",
        {"request": request}
    )


@router.get("/owner/tasks/templates")
async def owner_tasks_templates(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Библиотека шаблонов задач."""
    task_service = TaskService(session)
    templates_list = await task_service.get_templates_for_role(
        user_id=current_user.id,
        role="owner"
    )
    return templates.TemplateResponse(
        "owner/tasks/templates.html",
        {"request": request, "templates_list": templates_list}
    )


@router.post("/owner/tasks/templates/create")
async def owner_tasks_templates_create(
    request: Request,
    code: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    is_mandatory: int = Form(0),
    requires_media: int = Form(0),
    default_amount: str = Form(None),
    object_id: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать шаблон задачи."""
    from decimal import Decimal
    task_service = TaskService(session)
    
    amount = Decimal(default_amount) if default_amount else None
    obj_id = int(object_id) if object_id else None
    
    await task_service.create_template(
        owner_id=current_user.id,
        code=code,
        title=title,
        description=description,
        is_mandatory=bool(is_mandatory),
        requires_media=bool(requires_media),
        default_amount=amount,
        object_id=obj_id
    )
    
    return RedirectResponse(url="/owner/tasks/templates", status_code=303)


@router.get("/owner/tasks/plan")
async def owner_tasks_plan(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Планирование задач."""
    from domain.entities.task_plan import TaskPlanV2
    from domain.entities.object import Object
    from sqlalchemy.orm import selectinload
    
    owner_id = current_user.id
    
    # Получаем планы с eager loading template и object
    plans_query = select(TaskPlanV2).where(TaskPlanV2.owner_id == owner_id).options(
        selectinload(TaskPlanV2.template),
        selectinload(TaskPlanV2.object)
    ).order_by(TaskPlanV2.created_at.desc())
    plans_result = await session.execute(plans_query)
    plans = plans_result.scalars().all()
    
    # Получаем шаблоны и объекты для модала
    task_service = TaskService(session)
    templates_list = await task_service.get_templates_for_role(user_id=owner_id, role="owner")
    
    objects_query = select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name)
    objects_result = await session.execute(objects_query)
    objects_list = objects_result.scalars().all()
    
    return templates.TemplateResponse(
        "owner/tasks/plan.html",
        {"request": request, "plans": plans, "templates_list": templates_list, "objects_list": objects_list}
    )


@router.post("/owner/tasks/plan/create")
async def owner_tasks_plan_create(
    request: Request,
    template_id: int = Form(...),
    object_id: str = Form(None),
    planned_date: str = Form(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать план задачи."""
    from domain.entities.task_plan import TaskPlanV2
    from datetime import datetime
    from core.logging.logger import logger
    
    owner_id = current_user.id
    obj_id = int(object_id) if object_id else None
    p_date = datetime.fromisoformat(planned_date) if planned_date else None
    
    plan = TaskPlanV2(
        template_id=template_id,
        owner_id=owner_id,
        object_id=obj_id,
        planned_date=p_date,
        is_active=True
    )
    session.add(plan)
    await session.commit()
    logger.info(f"Created TaskPlanV2: {plan.id}, template={template_id}, object={obj_id}")
    
    return RedirectResponse(url="/owner/tasks/plan", status_code=303)


@router.post("/owner/tasks/plan/{plan_id}/toggle")
async def owner_tasks_plan_toggle(
    request: Request,
    plan_id: int,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Toggle активности плана."""
    from domain.entities.task_plan import TaskPlanV2
    
    plan = await session.get(TaskPlanV2, plan_id)
    if plan and plan.owner_id == current_user.id:
        plan.is_active = not plan.is_active
        await session.commit()
    
    return RedirectResponse(url="/owner/tasks/plan", status_code=303)


@router.get("/owner/tasks/entries")
async def owner_tasks_entries(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Выполнение и аудит задач."""
    from domain.entities.task_entry import TaskEntryV2
    from domain.entities.task_plan import TaskPlanV2
    from domain.entities.task_template import TaskTemplateV2
    from domain.entities.object import Object
    from sqlalchemy.orm import selectinload
    
    owner_id = current_user.id
    
    # Получаем entries с eager loading всех связей
    entries_query = (
        select(TaskEntryV2)
        .join(TaskPlanV2, TaskEntryV2.plan_id == TaskPlanV2.id, isouter=True)
        .join(TaskTemplateV2, TaskEntryV2.template_id == TaskTemplateV2.id, isouter=True)
        .where(or_(TaskPlanV2.owner_id == owner_id, TaskTemplateV2.owner_id == owner_id))
        .options(
            selectinload(TaskEntryV2.template),
            selectinload(TaskEntryV2.plan).selectinload(TaskPlanV2.object),
            selectinload(TaskEntryV2.employee)
        )
        .order_by(TaskEntryV2.created_at.desc())
        .limit(100)
    )
    entries_result = await session.execute(entries_query)
    entries = entries_result.scalars().all()
    
    return templates.TemplateResponse(
        "owner/tasks/entries.html",
        {"request": request, "entries": entries}
    )

