"""Сервис для записи истории операций со сменами."""

from __future__ import annotations

from typing import Optional, Dict, Any, Iterable, List

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.shift_history import ShiftHistory
from core.logging.logger import logger


class ShiftHistoryService:
    """Сервис записи истории операций над сменами и расписаниями."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def log_event(
        self,
        *,
        operation: str,
        source: str,
        actor_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        shift_id: Optional[int] = None,
        schedule_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ShiftHistory:
        """Записать единичное событие."""
        history = ShiftHistory(
            operation=operation,
            source=source,
            actor_id=actor_id,
            actor_role=actor_role,
            shift_id=shift_id,
            schedule_id=schedule_id,
            old_status=old_status,
            new_status=new_status,
            payload=payload or None,
        )
        self._session.add(history)
        await self._session.flush()

        logger.info(
            "Shift history recorded",
            operation=operation,
            source=source,
            actor_id=actor_id,
            actor_role=actor_role,
            shift_id=shift_id,
            schedule_id=schedule_id,
            old_status=old_status,
            new_status=new_status,
        )

        return history

    async def log_batch(self, events: Iterable[Dict[str, Any]]) -> List[ShiftHistory]:
        """Записать несколько событий пачкой."""
        histories: List[ShiftHistory] = []
        for event in events:
            histories.append(await self.log_event(**event))
        return histories

    async def fetch_history(
        self,
        *,
        schedule_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        limit: Optional[int] = None,
        order: str = "desc",
    ) -> List[ShiftHistory]:
        """
        Получить историю операций для указанной смены или расписания.

        Args:
            schedule_id: ID запланированной смены.
            shift_id: ID фактической смены.
            limit: Максимальное количество записей.
            order: Порядок сортировки, 'asc' или 'desc'.
        """
        if schedule_id is None and shift_id is None:
            raise ValueError("Either schedule_id or shift_id must be provided")

        stmt = select(ShiftHistory)

        conditions = []
        if schedule_id is not None:
            conditions.append(ShiftHistory.schedule_id == schedule_id)
        if shift_id is not None:
            conditions.append(ShiftHistory.shift_id == shift_id)

        if len(conditions) == 1:
            stmt = stmt.where(conditions[0])
        else:
            stmt = stmt.where(or_(*conditions))

        if order == "asc":
            stmt = stmt.order_by(ShiftHistory.created_at.asc())
        else:
            stmt = stmt.order_by(desc(ShiftHistory.created_at))

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

