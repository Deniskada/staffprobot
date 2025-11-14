"""Backfill shift_history для существующих смен/расписаний."""

import asyncio

from sqlalchemy import select

from core.database.session import get_async_session
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift_cancellation import ShiftCancellation
from shared.services.shift_history_service import ShiftHistoryService


async def backfill() -> None:
    async with get_async_session() as session:
        history_service = ShiftHistoryService(session)

        existing_histories = await session.execute(select(ShiftSchedule.id))
        schedule_ids_with_history = {row[0] for row in existing_histories}

        missing_schedules = await session.execute(
            select(ShiftSchedule).where(ShiftSchedule.id.notin_(schedule_ids_with_history))
        )

        for schedule in missing_schedules.scalars():
            await history_service.log_event(
                operation="schedule_plan",
                source="backfill",
                actor_id=schedule.user_id,
                actor_role="system",
                schedule_id=schedule.id,
                old_status=None,
                new_status=schedule.status,
                payload={
                    "object_id": schedule.object_id,
                    "planned_start": schedule.planned_start.isoformat() if schedule.planned_start else None,
                    "planned_end": schedule.planned_end.isoformat() if schedule.planned_end else None,
                },
            )

            cancellation = await session.execute(
                select(ShiftCancellation).where(ShiftCancellation.shift_schedule_id == schedule.id)
            )
            cancellation_obj = cancellation.scalar_one_or_none()
            if cancellation_obj:
                await history_service.log_event(
                    operation="schedule_cancel",
                    source="backfill",
                    actor_id=cancellation_obj.cancelled_by_id,
                    actor_role=cancellation_obj.cancelled_by_type,
                    schedule_id=schedule.id,
                    old_status="planned",
                    new_status="cancelled",
                    payload={
                        "reason_code": cancellation_obj.cancellation_reason,
                        "notes": cancellation_obj.reason_notes,
                    },
                )

        missing_shifts = await session.execute(select(Shift).where(Shift.schedule_id.is_(None)))
        for shift in missing_shifts.scalars():
            await history_service.log_event(
                operation="shift_open",
                source="backfill",
                actor_id=shift.user_id,
                actor_role="system",
                shift_id=shift.id,
                old_status=None,
                new_status=shift.status,
                payload={"object_id": shift.object_id},
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(backfill())

