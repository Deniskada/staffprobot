"""Роуты владельца для управления задачами (Tasks v2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.task_template import TaskTemplateV2
from domain.entities.task_plan import TaskPlanV2
from domain.entities.task_entry import TaskEntryV2
from domain.entities.user import User


router = APIRouter()


@router.get("/owner/tasks/templates")
async def owner_tasks_templates(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Библиотека шаблонов задач."""
    owner_id = current_user.id
    query = select(TaskTemplateV2).where(TaskTemplateV2.owner_id == owner_id).order_by(TaskTemplateV2.title)
    result = await session.execute(query)
    templates_list = result.scalars().all()
    return templates.TemplateResponse(
        "owner/tasks/templates.html",
        {"request": request, "templates_list": templates_list}
    )


@router.get("/owner/tasks/plan")
async def owner_tasks_plan(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Планирование задач."""
    return templates.TemplateResponse(
        "owner/tasks/plan.html",
        {"request": request}
    )


@router.get("/owner/tasks/entries")
async def owner_tasks_entries(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Выполнение и аудит задач."""
    owner_id = current_user.id
    query = select(TaskEntryV2).where(TaskEntryV2.template_id.in_(
        select(TaskTemplateV2.id).where(TaskTemplateV2.owner_id == owner_id)
    )).order_by(TaskEntryV2.created_at.desc()).limit(100)
    result = await session.execute(query)
    entries = result.scalars().all()
    return templates.TemplateResponse(
        "owner/tasks/entries.html",
        {"request": request, "entries": entries}
    )

