"""Сервис для синхронизации статусов расписаний и фактических смен."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from shared.services.shift_history_service import ShiftHistoryService


class ShiftStatusSyncService:
    """Утилита для выравнивания статусов ShiftSchedule и Shift."""

    _FINAL_STATUSES = {"cancelled", "completed"}

    def __init__(self, session: AsyncSession):
        self._session = session
        self._history_service = ShiftHistoryService(session)

    async def cancel_linked_shifts(
        self,
        schedule: Optional[ShiftSchedule],
        *,
        actor_id: Optional[int],
        actor_role: Optional[str],
        source: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Перевести связанные фактические смены в `cancelled`."""
        if not schedule:
            return 0

        shifts: List[Shift] = []
        # Проверяем, загружена ли коллекция actual_shifts без ленивого запроса.
        if "actual_shifts" in schedule.__dict__ and schedule.__dict__["actual_shifts"] is not None:
            shifts = list(schedule.__dict__["actual_shifts"])
        else:
            result = await self._session.execute(select(Shift).where(Shift.schedule_id == schedule.id))
            shifts = list(result.scalars().all())

        if not shifts:
            return 0

        cancelled_count = 0
        for shift in shifts:
            if shift.status in self._FINAL_STATUSES:
                continue

            previous_status = shift.status
            shift.status = "cancelled"

            # Зафиксируем окончание, чтобы не оставлять «бесконечные» смены.
            if shift.end_time is None:
                shift.end_time = datetime.now(timezone.utc)

            await self._history_service.log_event(
                operation="shift_cancel",
                source=source,
                actor_id=actor_id,
                actor_role=actor_role,
                shift_id=shift.id,
                schedule_id=shift.schedule_id,
                old_status=previous_status,
                new_status="cancelled",
                payload=payload or None,
            )
            cancelled_count += 1

        return cancelled_count

