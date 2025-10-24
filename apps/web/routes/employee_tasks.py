"""Роуты сотрудника для задач - использует shared TaskService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.user import User
from shared.services.task_service import TaskService
from sqlalchemy import select


router = APIRouter()


async def get_user_id_from_current_user(current_user, session: AsyncSession) -> int:
    """Получить внутренний user_id из current_user (может быть dict или User)."""
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        result = await session.execute(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        user_id = result.scalar_one_or_none()
        if not user_id:
            raise ValueError(f"User with telegram_id={telegram_id} not found")
        return user_id
    return current_user.id


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

