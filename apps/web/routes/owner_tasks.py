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
    task_service = TaskService(session)
    entries = await task_service.get_entries_for_role(
        user_id=current_user.id,
        role="owner",
        limit=100
    )
    return templates.TemplateResponse(
        "owner/tasks/entries.html",
        {"request": request, "entries": entries}
    )

