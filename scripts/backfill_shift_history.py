"""Backfill shift_history для существующих смен/расписаний."""

import asyncio

from sqlalchemy import select, distinct

from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift_cancellation import ShiftCancellation
from domain.entities.shift_history import ShiftHistory
from shared.services.shift_history_service import ShiftHistoryService


async def backfill() -> None:
    async with get_async_session() as session:
        history_service = ShiftHistoryService(session)

        # Получаем schedule_id, для которых уже есть история
        existing_schedule_histories = await session.execute(
            select(distinct(ShiftHistory.schedule_id)).where(ShiftHistory.schedule_id.isnot(None))
        )
        schedule_ids_with_history = {row[0] for row in existing_schedule_histories if row[0] is not None}

        # Получаем shift_id, для которых уже есть история
        existing_shift_histories = await session.execute(
            select(distinct(ShiftHistory.shift_id)).where(ShiftHistory.shift_id.isnot(None))
        )
        shift_ids_with_history = {row[0] for row in existing_shift_histories if row[0] is not None}

        logger.info(f"Найдено расписаний с историей: {len(schedule_ids_with_history)}")
        logger.info(f"Найдено смен с историей: {len(shift_ids_with_history)}")

        # Обрабатываем расписания без истории
        all_schedules = await session.execute(select(ShiftSchedule))
        schedules_processed = 0
        cancellations_processed = 0

        for schedule in all_schedules.scalars():
            # Пропускаем, если уже есть история
            if schedule.id in schedule_ids_with_history:
                continue

            # Создаем запись о планировании
            await history_service.log_event(
                operation="schedule_plan",
                source="backfill",
                actor_id=schedule.user_id,
                actor_role="system",
                schedule_id=schedule.id,
                old_status=None,
                new_status=schedule.status if schedule.status != "cancelled" else "planned",
                payload={
                    "object_id": schedule.object_id,
                    "planned_start": schedule.planned_start.isoformat() if schedule.planned_start else None,
                    "planned_end": schedule.planned_end.isoformat() if schedule.planned_end else None,
                },
            )
            schedules_processed += 1

            # Проверяем отмену
            cancellation_result = await session.execute(
                select(ShiftCancellation).where(ShiftCancellation.shift_schedule_id == schedule.id)
            )
            cancellation = cancellation_result.scalar_one_or_none()
            if cancellation:
                await history_service.log_event(
                    operation="schedule_cancel",
                    source="backfill",
                    actor_id=cancellation.cancelled_by_id,
                    actor_role=cancellation.cancelled_by_type or "employee",
                    schedule_id=schedule.id,
                    old_status="planned",
                    new_status="cancelled",
                    payload={
                        "reason_code": cancellation.cancellation_reason,
                        "notes": cancellation.reason_notes,
                    },
                )
                cancellations_processed += 1

        logger.info(f"Обработано расписаний: {schedules_processed}, отмен: {cancellations_processed}")

        # Обрабатываем фактические смены без истории
        all_shifts = await session.execute(select(Shift))
        shifts_processed = 0

        for shift in all_shifts.scalars():
            # Пропускаем, если уже есть история
            if shift.id in shift_ids_with_history:
                continue

            # Создаем запись об открытии смены
            await history_service.log_event(
                operation="shift_open",
                source="backfill",
                actor_id=shift.user_id,
                actor_role="system",
                shift_id=shift.id,
                schedule_id=shift.schedule_id,
                old_status=None,
                new_status=shift.status if shift.status not in ["cancelled", "completed"] else "active",
                payload={
                    "object_id": shift.object_id,
                    "start_time": shift.start_time.isoformat() if shift.start_time else None,
                },
            )
            shifts_processed += 1

            # Если смена завершена, создаем запись о закрытии
            if shift.status == "completed" and shift.end_time:
                await history_service.log_event(
                    operation="shift_close",
                    source="backfill",
                    actor_id=shift.user_id,
                    actor_role="system",
                    shift_id=shift.id,
                    schedule_id=shift.schedule_id,
                    old_status="active",
                    new_status="completed",
                    payload={
                        "object_id": shift.object_id,
                        "end_time": shift.end_time.isoformat() if shift.end_time else None,
                        "total_hours": float(shift.total_hours) if shift.total_hours else None,
                    },
                )

        logger.info(f"Обработано смен: {shifts_processed}")

        await session.commit()
        logger.info("Backfill завершен успешно")


if __name__ == "__main__":
    asyncio.run(backfill())

