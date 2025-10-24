"""Роуты управляющего для задач - использует shared TaskService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.user import User
from shared.services.task_service import TaskService
from shared.services.user_service import get_user_id_from_current_user


router = APIRouter()


@router.get("/manager/tasks/templates")
async def manager_tasks_templates(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["manager", "owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Библиотека шаблонов задач (фильтр по объектам управляющего)."""
    user_id = await get_user_id_from_current_user(current_user, session)
    task_service = TaskService(session)
    
    # Для manager передаём owner_id из контракта (нужно получить)
    # TODO: добавить получение owner_id из контракта manager
    owner_id = current_user.get("owner_id") if isinstance(current_user, dict) else None
    
    templates_list = await task_service.get_templates_for_role(
        user_id=user_id,
        role="manager",
        owner_id=owner_id
    )
    return templates.TemplateResponse(
        "manager/tasks/templates.html",
        {"request": request, "templates_list": templates_list}
    )


@router.get("/manager/tasks/entries")
async def manager_tasks_entries(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["manager", "owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Выполнение и аудит задач (фильтр по объектам управляющего)."""
    user_id = await get_user_id_from_current_user(current_user, session)
    task_service = TaskService(session)
    
    owner_id = current_user.get("owner_id") if isinstance(current_user, dict) else None
    
    entries = await task_service.get_entries_for_role(
        user_id=user_id,
        role="manager",
        owner_id=owner_id,
        limit=100
    )
    return templates.TemplateResponse(
        "manager/tasks/entries.html",
        {"request": request, "entries": entries}
    )

