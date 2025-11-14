"""Сервис для записи истории операций со сменами."""

from __future__ import annotations

from typing import Optional, Dict, Any, Iterable, List

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

