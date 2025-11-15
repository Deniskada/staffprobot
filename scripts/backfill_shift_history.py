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
from shared.services.shift_status_sync_service import ShiftStatusSyncService


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

        # Корректировка статусов Shift vs ShiftSchedule
        logger.info("Начинаем корректировку статусов Shift vs ShiftSchedule")
        sync_service = ShiftStatusSyncService(session)
        status_corrections = await correct_shift_statuses(session, history_service, sync_service)
        logger.info(
            f"Корректировка завершена: исправлено расписаний={status_corrections['schedules_fixed']}, "
            f"исправлено смен={status_corrections['shifts_fixed']}"
        )

        await session.commit()
        logger.info("Backfill завершен успешно")


async def correct_shift_statuses(
    session,
    history_service: ShiftHistoryService,
    sync_service: ShiftStatusSyncService,
) -> dict:
    """
    Корректировка несогласованных статусов Shift и ShiftSchedule.
    
    Правила:
    1. Если ShiftSchedule = cancelled, то связанные Shift должны быть cancelled (если не completed)
    2. Если ShiftSchedule = completed, то связанные Shift не могут быть active
    3. Если Shift = completed, то ShiftSchedule должна быть completed
    4. Если Shift = cancelled и связана с ShiftSchedule, то ShiftSchedule должна быть cancelled (если не completed)
    
    Returns:
        dict: Статистика исправлений
    """
    from sqlalchemy import select
    from datetime import datetime, timezone
    
    schedules_fixed = 0
    shifts_fixed = 0
    
    # Получаем все расписания с связанными сменами
    all_schedules = await session.execute(select(ShiftSchedule))
    
    for schedule in all_schedules.scalars():
        # Получаем связанные смены
        shifts_result = await session.execute(
            select(Shift).where(Shift.schedule_id == schedule.id)
        )
        related_shifts = list(shifts_result.scalars().all())
        
        if not related_shifts:
            continue
        
        # Правило 1: Если расписание отменено, отменяем все связанные смены (кроме completed)
        if schedule.status == "cancelled":
            for shift in related_shifts:
                if shift.status not in {"cancelled", "completed"}:
                    old_status = shift.status
                    shift.status = "cancelled"
                    if shift.end_time is None:
                        shift.end_time = datetime.now(timezone.utc)
                    
                    await history_service.log_event(
                        operation="shift_cancel",
                        source="backfill",
                        actor_id=None,
                        actor_role="system",
                        shift_id=shift.id,
                        schedule_id=schedule.id,
                        old_status=old_status,
                        new_status="cancelled",
                        payload={
                            "reason": "Корректировка: расписание отменено",
                            "object_id": shift.object_id,
                        },
                    )
                    shifts_fixed += 1
                    logger.info(
                        f"Исправлена смена {shift.id}: {old_status} → cancelled "
                        f"(расписание {schedule.id} отменено)"
                    )
        
        # Правило 2: Если расписание завершено, отменяем активные смены
        elif schedule.status == "completed":
            for shift in related_shifts:
                if shift.status == "active":
                    old_status = shift.status
                    shift.status = "cancelled"
                    if shift.end_time is None:
                        shift.end_time = datetime.now(timezone.utc)
                    
                    await history_service.log_event(
                        operation="shift_cancel",
                        source="backfill",
                        actor_id=None,
                        actor_role="system",
                        shift_id=shift.id,
                        schedule_id=schedule.id,
                        old_status=old_status,
                        new_status="cancelled",
                        payload={
                            "reason": "Корректировка: расписание завершено",
                            "object_id": shift.object_id,
                        },
                    )
                    shifts_fixed += 1
                    logger.info(
                        f"Исправлена смена {shift.id}: {old_status} → cancelled "
                        f"(расписание {schedule.id} завершено)"
                    )
        
        # Правило 3: Если есть завершенная смена, расписание должно быть completed
        has_completed_shift = any(s.status == "completed" for s in related_shifts)
        if has_completed_shift and schedule.status != "completed":
            old_status = schedule.status
            schedule.status = "completed"
            schedule.updated_at = datetime.now(timezone.utc)
            
            await history_service.log_event(
                operation="schedule_complete",
                source="backfill",
                actor_id=None,
                actor_role="system",
                schedule_id=schedule.id,
                shift_id=None,
                old_status=old_status,
                new_status="completed",
                payload={
                    "reason": "Корректировка: есть завершенная смена",
                    "object_id": schedule.object_id,
                },
            )
            schedules_fixed += 1
            logger.info(
                f"Исправлено расписание {schedule.id}: {old_status} → completed "
                f"(есть завершенная смена)"
            )
        
        # Правило 4: Если все смены отменены и расписание не completed, отменяем расписание
        all_shifts_cancelled = all(
            s.status == "cancelled" for s in related_shifts
        ) and len(related_shifts) > 0
        if all_shifts_cancelled and schedule.status not in {"cancelled", "completed"}:
            old_status = schedule.status
            schedule.status = "cancelled"
            schedule.updated_at = datetime.now(timezone.utc)
            
            await history_service.log_event(
                operation="schedule_cancel",
                source="backfill",
                actor_id=None,
                actor_role="system",
                schedule_id=schedule.id,
                shift_id=None,
                old_status=old_status,
                new_status="cancelled",
                payload={
                    "reason": "Корректировка: все связанные смены отменены",
                    "object_id": schedule.object_id,
                },
            )
            schedules_fixed += 1
            logger.info(
                f"Исправлено расписание {schedule.id}: {old_status} → cancelled "
                f"(все связанные смены отменены)"
            )
    
    return {
        "schedules_fixed": schedules_fixed,
        "shifts_fixed": shifts_fixed,
    }


if __name__ == "__main__":
    asyncio.run(backfill())

