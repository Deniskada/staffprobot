"""Сервис для синхронизации статусов расписаний и фактических смен."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from shared.services.shift_history_service import ShiftHistoryService
from core.logging.logger import logger


class ShiftStatusSyncService:
    """
    Утилита для выравнивания статусов ShiftSchedule и Shift.
    
    Матрица переходов статусов:
    - ShiftSchedule: planned, confirmed (legacy), cancelled, completed
    - Shift: active, cancelled, completed
    
    Правила синхронизации:
    1. При открытии смены из расписания: Shift = active, ShiftSchedule остается planned
    2. При закрытии смены: Shift = completed, ShiftSchedule = completed
    3. При отмене расписания: ShiftSchedule = cancelled, все связанные Shift = cancelled (если не completed)
    4. При отмене смены: Shift = cancelled, ShiftSchedule = cancelled (если связана)
    
    Запрещенные комбинации:
    - cancelled + active/completed (расписание отменено, смена не может быть активной/завершенной)
    - completed + active (расписание завершено, смена не может быть активной)
    """

    _FINAL_STATUSES = {"cancelled", "completed"}

    def __init__(self, session: AsyncSession):
        self._session = session
        self._history_service = ShiftHistoryService(session)

    async def sync_on_shift_open(
        self,
        shift: Shift,
        *,
        actor_id: Optional[int],
        actor_role: Optional[str],
        source: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Синхронизация статусов при открытии смены из расписания.
        
        Правило: ShiftSchedule остается planned (НЕ меняется на in_progress/active).
        Это позволяет использовать расписание для повторных смен.
        
        Args:
            shift: Открытая смена
            actor_id: ID пользователя, открывшего смену
            actor_role: Роль пользователя
            source: Источник операции (bot/web/celery)
            payload: Дополнительные данные для истории
            
        Returns:
            True если синхронизация выполнена, False если смена не связана с расписанием
        """
        if not shift.schedule_id:
            return False

        schedule_result = await self._session.execute(
            select(ShiftSchedule).where(ShiftSchedule.id == shift.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            logger.warning(
                f"Schedule {shift.schedule_id} not found for shift {shift.id}",
                shift_id=shift.id,
                schedule_id=shift.schedule_id,
            )
            return False

        # Проверяем запрещенные комбинации
        if schedule.status == "cancelled":
            logger.error(
                f"Cannot open shift from cancelled schedule",
                shift_id=shift.id,
                schedule_id=schedule.id,
                schedule_status=schedule.status,
            )
            # Отменяем смену, если расписание отменено
            shift.status = "cancelled"
            if shift.end_time is None:
                shift.end_time = datetime.now(timezone.utc)
            return False

        if schedule.status == "completed":
            logger.error(
                f"Cannot open shift from completed schedule",
                shift_id=shift.id,
                schedule_id=schedule.id,
                schedule_status=schedule.status,
            )
            # Отменяем смену, если расписание завершено
            shift.status = "cancelled"
            if shift.end_time is None:
                shift.end_time = datetime.now(timezone.utc)
            return False

        # ShiftSchedule остается planned (не меняем статус)
        # Логируем только факт открытия смены
        logger.info(
            f"Shift opened from schedule (schedule remains planned)",
            shift_id=shift.id,
            schedule_id=schedule.id,
            schedule_status=schedule.status,
        )

        return True

    async def sync_on_shift_close(
        self,
        shift: Shift,
        *,
        actor_id: Optional[int],
        actor_role: Optional[str],
        source: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Синхронизация статусов при закрытии смены.
        
        Правило: ShiftSchedule меняется на completed, если связана с закрытой сменой.
        
        Args:
            shift: Закрытая смена
            actor_id: ID пользователя, закрывшего смену
            actor_role: Роль пользователя
            source: Источник операции (bot/web/celery)
            payload: Дополнительные данные для истории
            
        Returns:
            True если синхронизация выполнена, False если смена не связана с расписанием
        """
        if not shift.schedule_id:
            return False

        schedule_result = await self._session.execute(
            select(ShiftSchedule).where(ShiftSchedule.id == shift.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            logger.warning(
                f"Schedule {shift.schedule_id} not found for shift {shift.id}",
                shift_id=shift.id,
                schedule_id=shift.schedule_id,
            )
            return False

        # Проверяем запрещенные комбинации
        if schedule.status == "cancelled":
            logger.warning(
                f"Cannot close shift from cancelled schedule, marking shift as cancelled",
                shift_id=shift.id,
                schedule_id=schedule.id,
            )
            shift.status = "cancelled"
            if shift.end_time is None:
                shift.end_time = datetime.now(timezone.utc)
            return False

        # Обновляем статус расписания на completed
        previous_schedule_status = schedule.status
        schedule.status = "completed"
        schedule.updated_at = datetime.now(timezone.utc)

        # Логируем изменение статуса расписания
        await self._history_service.log_event(
            operation="schedule_complete",
            source=source,
            actor_id=actor_id,
            actor_role=actor_role,
            schedule_id=schedule.id,
            shift_id=shift.id,
            old_status=previous_schedule_status,
            new_status="completed",
            payload=payload or None,
        )

        logger.info(
            f"Schedule status updated to completed",
            shift_id=shift.id,
            schedule_id=schedule.id,
            previous_status=previous_schedule_status,
        )

        return True

    async def sync_on_shift_cancel(
        self,
        shift: Shift,
        *,
        actor_id: Optional[int],
        actor_role: Optional[str],
        source: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Синхронизация статусов при отмене фактической смены.
        
        Правило: ShiftSchedule меняется на cancelled, если связана с отмененной сменой.
        
        Args:
            shift: Отмененная смена
            actor_id: ID пользователя, отменившего смену
            actor_role: Роль пользователя
            source: Источник операции (bot/web/celery)
            payload: Дополнительные данные для истории
            
        Returns:
            True если синхронизация выполнена, False если смена не связана с расписанием
        """
        if not shift.schedule_id:
            return False

        schedule_result = await self._session.execute(
            select(ShiftSchedule).where(ShiftSchedule.id == shift.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            logger.warning(
                f"Schedule {shift.schedule_id} not found for shift {shift.id}",
                shift_id=shift.id,
                schedule_id=shift.schedule_id,
            )
            return False

        # Не отменяем расписание, если смена уже завершена
        if shift.status == "completed":
            logger.info(
                f"Cannot cancel schedule for completed shift",
                shift_id=shift.id,
                schedule_id=schedule.id,
            )
            return False

        # Обновляем статус расписания на cancelled
        previous_schedule_status = schedule.status
        if schedule.status != "cancelled":
            schedule.status = "cancelled"
            schedule.updated_at = datetime.now(timezone.utc)

            # Логируем изменение статуса расписания
            await self._history_service.log_event(
                operation="schedule_cancel",
                source=source,
                actor_id=actor_id,
                actor_role=actor_role,
                schedule_id=schedule.id,
                shift_id=shift.id,
                old_status=previous_schedule_status,
                new_status="cancelled",
                payload=payload or None,
            )

            logger.info(
                f"Schedule status updated to cancelled",
                shift_id=shift.id,
                schedule_id=schedule.id,
                previous_status=previous_schedule_status,
            )

        return True

    async def sync_on_schedule_cancel(
        self,
        schedule: ShiftSchedule,
        *,
        actor_id: Optional[int],
        actor_role: Optional[str],
        source: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Синхронизация статусов при отмене расписания.
        
        Правило: Все связанные Shift меняются на cancelled (если не completed).
        
        Args:
            schedule: Отмененное расписание
            actor_id: ID пользователя, отменившего расписание
            actor_role: Роль пользователя
            source: Источник операции (bot/web/celery/contract)
            payload: Дополнительные данные для истории
            
        Returns:
            Количество отмененных смен
        """
        return await self.cancel_linked_shifts(
            schedule,
            actor_id=actor_id,
            actor_role=actor_role,
            source=source,
            payload=payload,
        )

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

