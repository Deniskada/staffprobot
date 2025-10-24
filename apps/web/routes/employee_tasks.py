"""Роуты сотрудника для задач - использует shared TaskService."""

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


@router.get("/employee/tasks/my")
async def employee_my_tasks(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["employee", "manager", "owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Мои задачи (сотрудник)."""
    user_id = await get_user_id_from_current_user(current_user, session)
    task_service = TaskService(session)
    
    entries = await task_service.get_entries_for_role(
        user_id=user_id,
        role="employee",
        limit=50
    )
    return templates.TemplateResponse(
        "employee/tasks/my.html",
        {"request": request, "entries": entries}
    )

