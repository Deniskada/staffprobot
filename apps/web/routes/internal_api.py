"""Внутренний API для межсервисной коммуникации (X-Internal-Token auth)."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Path
from pydantic import BaseModel
from sqlalchemy import select, and_, cast, Date, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from core.config.settings import settings
from core.database.session import get_db_session
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.shift import Shift

router = APIRouter(prefix="/api/internal", tags=["Internal API"])


def _check_token(x_internal_token: str = Header(...)):
    if not settings.internal_api_token or x_internal_token != settings.internal_api_token:
        raise HTTPException(status_code=403, detail="Forbidden")


async def _get_user_by_telegram(telegram_id: int, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Schemas ──────────────────────────────────────────────────────────────────

class OpenShiftRequest(BaseModel):
    telegram_id: int
    object_id: int
    latitude: float
    longitude: float


class CloseShiftRequest(BaseModel):
    telegram_id: int
    shift_id: int
    latitude: float
    longitude: float


class CompleteTaskRequest(BaseModel):
    telegram_id: int
    notes: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/objects")
async def get_objects(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(_check_token),
):
    """Список объектов, к которым привязан сотрудник."""
    user = await _get_user_by_telegram(telegram_id, db)

    result = await db.execute(
        select(Contract).where(
            and_(
                Contract.employee_id == user.id,
                Contract.is_active == True,
            )
        )
    )
    contracts = result.scalars().all()

    obj_ids: set[int] = set()
    for c in contracts:
        if c.allowed_objects:
            obj_ids.update(c.allowed_objects)
        # Contract has no direct object_id — allowed_objects is the only source

    if not obj_ids:
        return []

    result = await db.execute(select(Object).where(Object.id.in_(obj_ids)))
    objects = result.scalars().all()
    return [{"id": o.id, "name": o.name, "address": o.address} for o in objects]


@router.get("/shifts/active")
async def get_active_shift(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(_check_token),
):
    """Активная смена сотрудника или null."""
    user = await _get_user_by_telegram(telegram_id, db)

    result = await db.execute(
        select(Shift).where(
            and_(Shift.user_id == user.id, Shift.status == "active")
        )
    )
    shift = result.scalar_one_or_none()
    if not shift:
        return None

    obj_result = await db.execute(select(Object).where(Object.id == shift.object_id))
    obj = obj_result.scalar_one_or_none()
    return {
        "id": shift.id,
        "object_id": shift.object_id,
        "object_name": obj.name if obj else None,
        "started_at": shift.start_time.isoformat() if shift.start_time else None,
    }


@router.post("/shifts/open")
async def open_shift(
    body: OpenShiftRequest,
    _: None = Depends(_check_token),
):
    """Открыть смену."""
    from apps.bot.services.shift_service import ShiftService
    svc = ShiftService()
    coordinates = f"{body.latitude},{body.longitude}"
    result = await svc.open_shift(
        user_id=body.telegram_id,
        object_id=body.object_id,
        coordinates=coordinates,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Ошибка открытия смены"))
    return result


@router.post("/shifts/close")
async def close_shift(
    body: CloseShiftRequest,
    _: None = Depends(_check_token),
):
    """Закрыть смену."""
    from apps.bot.services.shift_service import ShiftService
    svc = ShiftService()
    coordinates = f"{body.latitude},{body.longitude}"
    result = await svc.close_shift(
        user_id=body.telegram_id,
        shift_id=body.shift_id,
        coordinates=coordinates,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Ошибка закрытия смены"))
    return result


@router.get("/tasks")
async def get_tasks(
    telegram_id: int = Query(...),
    date: Optional[date_type] = Query(default=None, description="Дата задач (по умолчанию — сегодня)"),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(_check_token),
):
    """Незавершённые задачи сотрудника на указанную дату (по умолчанию сегодня)."""
    from shared.services.task_service import TaskService
    from domain.entities.task_entry import TaskEntryV2
    from domain.entities.task_plan import TaskPlanV2
    from sqlalchemy.orm import selectinload

    user = await _get_user_by_telegram(telegram_id, db)
    target_date = date or date_type.today()

    # Задачи на конкретную дату: либо по planned_date плана, либо созданные сегодня
    query = (
        select(TaskEntryV2)
        .outerjoin(TaskPlanV2, TaskEntryV2.plan_id == TaskPlanV2.id)
        .options(selectinload(TaskEntryV2.template))
        .where(
            TaskEntryV2.employee_id == user.id,
            TaskEntryV2.is_completed == False,
            and_(
                # Входят задачи: запланированы на эту дату ИЛИ созданы сегодня (без плана)
                (
                    cast(TaskPlanV2.planned_date, Date) == target_date
                ) | (
                    (TaskEntryV2.plan_id == None) &
                    (cast(TaskEntryV2.created_at, Date) == target_date)
                )
            )
        )
        .order_by(TaskEntryV2.created_at)
        .limit(100)
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    return [
        {
            "id": e.id,
            "title": (e.template.title if e.template else None) or str(e.id),
            "description": (e.template.description if e.template else None) or "",
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "planned_date": target_date.isoformat(),
        }
        for e in entries
    ]


@router.post("/tasks/{entry_id}/complete")
async def complete_task(
    entry_id: int = Path(...),
    body: CompleteTaskRequest = ...,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(_check_token),
):
    """Отметить задачу как выполненную."""
    from shared.services.task_service import TaskService
    # Validate user exists
    await _get_user_by_telegram(body.telegram_id, db)
    svc = TaskService(db)
    ok = await svc.mark_entry_completed(
        entry_id=entry_id,
        completion_notes=body.notes or None,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}
