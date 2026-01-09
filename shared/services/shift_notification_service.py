"""Сервис уведомлений для событий, связанных со сменами."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from core.logging.logger import logger
from core.utils.timezone_helper import timezone_helper
from domain.entities.cancellation_reason import CancellationReason
from domain.entities.contract import Contract
from domain.entities.notification import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from domain.entities.notification import Notification
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from shared.services.cancellation_policy_service import CancellationPolicyService
from shared.services.notification_service import NotificationService
from shared.services.manager_permission_service import ManagerPermissionService
from shared.templates.notifications.base_templates import NotificationTemplateManager


class ShiftNotificationService:
    """Единая точка отправки уведомлений о сменах."""

    def __init__(self) -> None:
        self._notification_service = NotificationService()

    async def notify_schedule_planned(
        self,
        schedule_id: int,
        actor_role: str,
        planner_id: Optional[int] = None,
    ) -> None:
        """Уведомить владельца о планировании смены сотрудником."""
        if (actor_role or "").lower() != "employee":
            return

        async with get_async_session() as session:
            schedule = await self._load_schedule(session, schedule_id)
            if not schedule or not schedule.object or not schedule.user:
                return

            owner_id = schedule.object.owner_id
            if not owner_id or owner_id == planner_id:
                return

            channels = await self._get_channels(owner_id, NotificationType.SHIFT_CONFIRMED)
            if not channels:
                return

            employee_name = self._build_user_name(schedule.user.first_name, schedule.user.last_name, schedule.user.username)
            shift_window = self._format_shift_window(schedule.planned_start, schedule.planned_end, schedule.object.timezone)

            data = {
                "shift_schedule_id": schedule.id,
                "object_id": schedule.object_id,
                "object_name": schedule.object.name,
                "employee_id": schedule.user_id,
                "employee_name": employee_name,
                "shift_window": shift_window,
                "shift_time": shift_window,
                "user_name": employee_name,
            }
            title = "Сотрудник запланировал смену"
            message = (
                f"{employee_name} запланировал смену на объекте «{schedule.object.name}».\n"
                f"Время: {shift_window}."
            )

            # Отправляем уведомление владельцу
            try:
                await self._send(owner_id, NotificationType.SHIFT_CONFIRMED, channels, title, message, data)
            except Exception as exc:
                logger.error(
                    "Failed to send shift confirmed notification to owner",
                    owner_id=owner_id,
                    schedule_id=schedule_id,
                    error=str(exc),
                )
            
            # Отправляем уведомления управляющим
            try:
                manager_user_ids = await self._get_managers_for_object(session, schedule.object_id)
                for manager_user_id in manager_user_ids:
                    try:
                        manager_channels = await self._get_channels(manager_user_id, NotificationType.SHIFT_CONFIRMED)
                        if manager_channels:
                            await self._send(manager_user_id, NotificationType.SHIFT_CONFIRMED, manager_channels, title, message, data)
                    except Exception as manager_exc:
                        # Ошибка при отправке одному менеджеру не должна останавливать остальных
                        logger.error(
                            "Failed to send shift confirmed notification to manager",
                            manager_user_id=manager_user_id,
                            schedule_id=schedule_id,
                            error=str(manager_exc),
                        )
                        continue
            except Exception as exc:
                logger.error(
                    "Failed to get managers or send notifications",
                    schedule_id=schedule_id,
                    error=str(exc),
                )

    async def notify_schedule_cancelled(
        self,
        schedule_id: int,
        actor_role: str,
        cancelled_by_user_id: Optional[int],
        reason_code: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Уведомления при отмене смены."""
        if session is None:
            async with get_async_session() as new_session:
                await self._notify_schedule_cancelled_impl(
                    schedule_id, actor_role, cancelled_by_user_id, reason_code, new_session
                )
        else:
            await self._notify_schedule_cancelled_impl(
                schedule_id, actor_role, cancelled_by_user_id, reason_code, session
            )
    
    async def _notify_schedule_cancelled_impl(
        self,
        schedule_id: int,
        actor_role: str,
        cancelled_by_user_id: Optional[int],
        reason_code: str,
        session: AsyncSession,
    ) -> None:
        """Внутренняя реализация уведомлений при отмене смены."""
        schedule = await self._load_schedule(session, schedule_id)
        if not schedule or not schedule.object:
            return

        owner_id = schedule.object.owner_id
        employee_id = schedule.user_id

        if not owner_id and not employee_id:
            return

        reason_title = await self._get_reason_title(session, schedule.object.owner_id, reason_code)
        shift_window = self._format_shift_window(schedule.planned_start, schedule.planned_end, schedule.object.timezone)
        employee_name = None
        if schedule.user:
            employee_name = self._build_user_name(
                schedule.user.first_name,
                schedule.user.last_name,
                schedule.user.username,
            )

        data = {
            "shift_schedule_id": schedule.id,
            "object_id": schedule.object_id,
            "object_name": schedule.object.name,
            "employee_id": schedule.user_id,
            "employee_name": employee_name,
            "user_name": employee_name,  # Для шаблона (для сотрудника)
            "shift_window": shift_window,
            "reason_code": reason_code,
            "reason_title": reason_title,
            "shift_time": shift_window,
            "cancellation_reason": reason_title,
        }

        recipients: List[Tuple[int, NotificationType, str, str]] = []
        actor = (actor_role or "").lower()

        # Определяем сообщения для владельца и управляющих
        owner_title = None
        owner_message = None
        
        if owner_id:
            if actor == "employee":
                owner_title = "Сотрудник отменил смену"
                owner_message = (
                    f"{employee_name or 'Сотрудник'} отменил смену на объекте «{schedule.object.name}».\n"
                    f"Время: {shift_window}.\n"
                    f"Причина: {reason_title}."
                )
            elif actor == "system":
                owner_title = "Смена отменена системой"
                owner_message = (
                    f"Смена на объекте «{schedule.object.name}» отменена системой.\n"
                    f"Время: {shift_window}.\n"
                    f"Причина: {reason_title}."
                )
            else:
                # Владелец или менеджер отменили — уведомим владельца для истории
                owner_title = "Смена отменена"
                owner_message = (
                    f"Смена на объекте «{schedule.object.name}» была отменена ({reason_title}).\n"
                    f"Время: {shift_window}."
                )
            
            if owner_title and owner_message:
                recipients.append((owner_id, NotificationType.SHIFT_CANCELLED, owner_title, owner_message))
                
                # Отправляем уведомления управляющим
                manager_user_ids = await self._get_managers_for_object(session, schedule.object_id)
                for manager_user_id in manager_user_ids:
                    recipients.append((manager_user_id, NotificationType.SHIFT_CANCELLED, owner_title, owner_message))

        if employee_id and (actor in {"owner", "manager", "superadmin", "system"}):
            title = "Ваша смена отменена"
            if actor == "system":
                message = (
                    f"Смена на объекте «{schedule.object.name}» отменена системой.\n"
                    f"Время: {shift_window}.\n"
                    f"Причина: {reason_title}."
                )
            else:
                message = (
                    f"Владелец отменил вашу смену на объекте «{schedule.object.name}».\n"
                    f"Время: {shift_window}.\n"
                    f"Причина: {reason_title}."
                )
            recipients.append((employee_id, NotificationType.SHIFT_CANCELLED, title, message))

        await self._send_bulk(recipients, data)

    async def notify_shift_started(
        self,
        shift_id: int,
        actor_role: str,
    ) -> None:
        """Уведомить владельца о начале смены."""
        async with get_async_session() as session:
            shift = await self._load_shift(session, shift_id)
            if not shift or not shift.object or not shift.user:
                return

            owner_id = shift.object.owner_id
            if not owner_id:
                logger.debug(
                    "No owner_id for shift, skipping notification",
                    shift_id=shift_id,
                    object_id=shift.object_id if shift.object else None,
                )
                return

            channels = await self._get_channels(owner_id, NotificationType.SHIFT_STARTED)
            if not channels:
                logger.warning(
                    "No notification channels enabled for owner, skipping shift started notification",
                    owner_id=owner_id,
                    shift_id=shift_id,
                    notification_type=NotificationType.SHIFT_STARTED.value,
                )
                return

            employee_name = self._build_user_name(shift.user.first_name, shift.user.last_name, shift.user.username)
            started_at = timezone_helper.format_local_time(shift.start_time, shift.object.timezone, "%d.%m.%Y %H:%M")

            data = {
                "shift_id": shift.id,
                "schedule_id": shift.schedule_id,
                "object_id": shift.object_id,
                "object_name": shift.object.name,
                "employee_id": shift.user_id,
                "employee_name": employee_name,
                "started_at": started_at,
                "start_time": started_at,
                "user_name": employee_name,
            }

            title = "Смена началась"
            message = (
                f"{employee_name} начал смену на объекте «{shift.object.name}» в {started_at}."
            )

            # Отправляем уведомление владельцу
            try:
                await self._send(owner_id, NotificationType.SHIFT_STARTED, channels, title, message, data)
            except Exception as exc:
                logger.error(
                    "Failed to send shift started notification to owner",
                    owner_id=owner_id,
                    shift_id=shift_id,
                    error=str(exc),
                )
            
            # Отправляем уведомления управляющим
            try:
                manager_user_ids = await self._get_managers_for_object(session, shift.object_id)
                for manager_user_id in manager_user_ids:
                    try:
                        manager_channels = await self._get_channels(manager_user_id, NotificationType.SHIFT_STARTED)
                        if manager_channels:
                            await self._send(manager_user_id, NotificationType.SHIFT_STARTED, manager_channels, title, message, data)
                    except Exception as manager_exc:
                        # Ошибка при отправке одному менеджеру не должна останавливать остальных
                        logger.error(
                            "Failed to send shift started notification to manager",
                            manager_user_id=manager_user_id,
                            shift_id=shift_id,
                            error=str(manager_exc),
                        )
                        continue
            except Exception as exc:
                logger.error(
                    "Failed to get managers or send notifications",
                    shift_id=shift_id,
                    error=str(exc),
                )

    async def notify_shift_completed(
        self,
        shift_id: int,
        actor_role: str,
        total_hours: Optional[float] = None,
        total_payment: Optional[float] = None,
        auto: bool = False,
        finished_at: Optional[datetime] = None,
    ) -> None:
        """Уведомить о завершении смены."""
        async with get_async_session() as session:
            shift = await self._load_shift(session, shift_id)
            if not shift or not shift.object or not shift.user:
                return

            owner_id = shift.object.owner_id
            if not owner_id:
                return

            channels = await self._get_channels(owner_id, NotificationType.SHIFT_COMPLETED)
            if not channels:
                return

            if total_hours is None:
                total_hours = float(shift.total_hours) if shift.total_hours is not None else None
            if total_payment is None and shift.total_payment is not None:
                total_payment = float(shift.total_payment)

            employee_name = self._build_user_name(shift.user.first_name, shift.user.last_name, shift.user.username)
            finished_dt = finished_at if finished_at is not None else shift.end_time
            finished_at_text = timezone_helper.format_local_time(finished_dt, shift.object.timezone, "%d.%m.%Y %H:%M") if finished_dt else "Неизвестно"

            duration_text = "Неизвестно"
            if total_hours is not None:
                duration_text = f"{total_hours:.2f} ч"

            data = {
                "shift_id": shift.id,
                "schedule_id": shift.schedule_id,
                "object_id": shift.object_id,
                "object_name": shift.object.name,
                "employee_id": shift.user_id,
                "employee_name": employee_name,
                "finished_at": finished_at_text,
                "user_name": employee_name,
                "auto": auto,
                "total_hours": total_hours,
                "total_payment": total_payment,
                "duration": duration_text,
            }

            title = "Смена завершена"
            if auto:
                title = "Смена закрыта автоматически"

            parts = [
                f"{employee_name} завершил смену на объекте «{shift.object.name}».",
                f"Время окончания: {finished_at_text}.",
            ]
            if total_hours is not None:
                parts.append(f"Отработано часов: {total_hours:.2f}.")
            if total_payment is not None:
                parts.append(f"Расчётная оплата: {total_payment:.2f} ₽.")
            if auto:
                parts.append("Смена закрыта автоматически.")

            message = "\n".join(parts)

            # Отправляем уведомление владельцу
            try:
                await self._send(owner_id, NotificationType.SHIFT_COMPLETED, channels, title, message, data)
            except Exception as exc:
                logger.error(
                    "Failed to send shift completed notification to owner",
                    owner_id=owner_id,
                    shift_id=shift_id,
                    error=str(exc),
                )
            
            # Отправляем уведомления управляющим
            try:
                manager_user_ids = await self._get_managers_for_object(session, shift.object_id)
                for manager_user_id in manager_user_ids:
                    try:
                        manager_channels = await self._get_channels(manager_user_id, NotificationType.SHIFT_COMPLETED)
                        if manager_channels:
                            await self._send(manager_user_id, NotificationType.SHIFT_COMPLETED, manager_channels, title, message, data)
                    except Exception as manager_exc:
                        # Ошибка при отправке одному менеджеру не должна останавливать остальных
                        logger.error(
                            "Failed to send shift completed notification to manager",
                            manager_user_id=manager_user_id,
                            shift_id=shift_id,
                            error=str(manager_exc),
                        )
                        continue
            except Exception as exc:
                logger.error(
                    "Failed to get managers or send notifications",
                    shift_id=shift_id,
                    error=str(exc),
                )

    async def notify_shift_reminder(self, schedule_id: int) -> bool:
        """Отправить напоминание сотруднику о предстоящей смене."""
        async with get_async_session() as session:
            schedule = await self._load_schedule(session, schedule_id)
            if not schedule or not schedule.user:
                return False

            channels = await self._get_channels(schedule.user_id, NotificationType.SHIFT_REMINDER)
            if not channels:
                return False

            # Проверяем, не существует ли уже напоминание
            if await self._shift_notification_exists(session, schedule.user_id, NotificationType.SHIFT_REMINDER, schedule.id):
                logger.debug(
                    "Shift reminder already exists",
                    schedule_id=schedule.id,
                    user_id=schedule.user_id,
                )
                return False

            object_name = schedule.object.name if schedule.object else "Неизвестный объект"
            object_address = schedule.object.address if schedule.object else ""
            local_start = timezone_helper.utc_to_local(schedule.planned_start, schedule.object.timezone)
            local_end = timezone_helper.utc_to_local(schedule.planned_end, schedule.object.timezone)
            shift_time = f"{local_start.strftime('%H:%M')} - {local_end.strftime('%H:%M')}" if local_start and local_end else "Неизвестно"
            start_text = local_start.strftime("%d.%m.%Y %H:%M") if local_start else "Неизвестно"

            user_display_name = self._build_user_name(
                schedule.user.first_name,
                schedule.user.last_name,
                schedule.user.username,
            )

            # Вычисляем время до начала смены
            now = datetime.now(timezone.utc)
            time_until_str = "1 час"  # По умолчанию
            if schedule.planned_start:
                time_diff = schedule.planned_start - now
                if time_diff.total_seconds() > 0:
                    hours = int(time_diff.total_seconds() / 3600)
                    minutes = int((time_diff.total_seconds() % 3600) / 60)
                    if hours > 0:
                        time_until_str = f"{hours} ч"
                        if minutes > 0:
                            time_until_str += f" {minutes} мин"
                    else:
                        time_until_str = f"{minutes} мин"
            
            data = {
                "shift_schedule_id": schedule.id,
                "object_id": schedule.object_id,
                "object_name": object_name,
                "shift_time": shift_time,
                "shift_start": start_text,
                "address": object_address,
                "object_address": object_address,  # Для шаблона
                "user_name": user_display_name,
                "time_until": time_until_str,  # Для шаблона
            }

            title = "Напоминание о смене"
            message = (
                f"Ваша смена на объекте «{object_name}» начинается через 1 час.\n"
                f"Начало: {start_text}\n"
                f"Продолжительность: {shift_time}\n"
                f"Адрес: {object_address}"
            )

            await self._send(schedule.user_id, NotificationType.SHIFT_REMINDER, channels, title, message, data, priority=NotificationPriority.HIGH)
            return True

    async def _send_bulk(
        self,
        entries: Iterable[Tuple[int, NotificationType, str, str]],
        data: Dict[str, Optional[str]],
    ) -> None:
        sent_pairs: set[Tuple[int, NotificationChannel]] = set()
        for user_id, notif_type, title, message in entries:
            if not user_id:
                continue
            try:
                channels = await self._get_channels(user_id, notif_type)
                if not channels:
                    continue
                for channel in channels:
                    key = (user_id, channel)
                    if key in sent_pairs:
                        continue
                    try:
                        await self._send(user_id, notif_type, [channel], title, message, data)
                        sent_pairs.add(key)
                    except Exception as send_exc:
                        # Ошибка при отправке одному получателю не должна останавливать остальных
                        logger.error(
                            "Failed to send notification in bulk",
                            user_id=user_id,
                            notification_type=notif_type.value,
                            channel=channel.value,
                            error=str(send_exc),
                        )
                        # Продолжаем обработку остальных получателей
                        continue
            except Exception as exc:
                # Ошибка при получении каналов не должна останавливать остальных
                logger.error(
                    "Failed to get channels for user in bulk send",
                    user_id=user_id,
                    notification_type=notif_type.value,
                    error=str(exc),
                )
                # Продолжаем обработку остальных получателей
                continue

    async def _send(
        self,
        user_id: int,
        notif_type: NotificationType,
        channels: Iterable[NotificationChannel],
        title: str,
        message: str,
        data: Optional[Dict[str, Optional[str]]],
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> None:
        # Подготавливаем переменные для шаблонов (все значения должны быть строками)
        template_vars: Dict[str, str] = {}
        if data:
            for key, value in data.items():
                if value is not None:
                    template_vars[key] = str(value)
        
        for channel in channels:
            try:
                # Используем шаблоны для рендеринга title и message
                try:
                    rendered = NotificationTemplateManager.render(
                        notification_type=notif_type,
                        channel=channel,
                        variables=template_vars
                    )
                    rendered_title = rendered.get("title", title)
                    rendered_message = rendered.get("message", message)
                except Exception as template_exc:
                    # Fallback на готовые title/message, если шаблон не найден или ошибка
                    logger.warning(
                        "Failed to render notification template, using fallback",
                        notification_type=notif_type.value,
                        channel=channel.value,
                        error=str(template_exc),
                    )
                    rendered_title = title
                    rendered_message = message
                
                notification = await self._notification_service.create_notification(
                    user_id=user_id,
                    type=notif_type,
                    channel=channel,
                    title=rendered_title,
                    message=rendered_message,
                    data=data,
                    priority=priority,
                )
                
                # Автоматически отправляем уведомление через Celery
                if notification:
                    try:
                        from core.celery.tasks.notification_tasks import send_notification_now
                        send_notification_now.apply_async(
                            args=[notification.id],
                            queue="notifications"
                        )
                        logger.debug(
                            "Enqueued shift notification for sending",
                            notification_id=notification.id,
                            user_id=user_id,
                            notification_type=notif_type.value,
                            channel=channel.value,
                        )
                    except Exception as send_exc:
                        # Не критично, если не удалось поставить в очередь - уведомление уже в БД
                        logger.warning(
                            "Failed to enqueue notification for sending",
                            notification_id=notification.id if notification else None,
                            error=str(send_exc),
                        )
            except Exception as exc:
                logger.error(
                    "Failed to create shift notification",
                    user_id=user_id,
                    notification_type=notif_type.value,
                    channel=channel.value,
                    error=str(exc),
                )

    async def _get_channels(self, user_id: int, notif_type: NotificationType) -> List[NotificationChannel]:
        """Возвращает список каналов, включённых пользователем для указанного типа."""
        try:
            settings = await self._notification_service.get_user_notification_settings(user_id)
        except Exception as exc:
            logger.error(
                "Failed to load notification settings",
                user_id=user_id,
                notification_type=notif_type.value,
                error=str(exc),
            )
            settings = {}

        prefs = settings.get(notif_type.value, {})
        channels: List[NotificationChannel] = []

        if prefs.get("inapp", True):
            channels.append(NotificationChannel.IN_APP)
        if prefs.get("telegram", True):
            channels.append(NotificationChannel.TELEGRAM)
        if prefs.get("email", False):
            channels.append(NotificationChannel.EMAIL)
        if prefs.get("sms", False):
            channels.append(NotificationChannel.SMS)

        logger.debug(
            "Notification channels for user",
            user_id=user_id,
            notification_type=notif_type.value,
            settings=settings,
            prefs=prefs,
            channels=[ch.value for ch in channels],
        )

        return channels

    async def _load_schedule(self, session, schedule_id: int) -> Optional[ShiftSchedule]:
        result = await session.execute(
            select(ShiftSchedule)
            .options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.user),
            )
            .where(ShiftSchedule.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def _load_shift(self, session, shift_id: int) -> Optional[Shift]:
        result = await session.execute(
            select(Shift)
            .options(
                selectinload(Shift.object),
                selectinload(Shift.user),
            )
            .where(Shift.id == shift_id)
        )
        return result.scalar_one_or_none()

    async def _shift_notification_exists(
        self,
        session,
        user_id: int,
        notif_type: NotificationType,
        schedule_id: int,
    ) -> bool:
        expr = Notification.data["shift_schedule_id"].astext
        result = await session.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.type == notif_type,
                    expr == str(schedule_id),
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def _get_reason_title(
        self,
        session,
        owner_id: Optional[int],
        reason_code: str,
    ) -> str:
        if not owner_id:
            return reason_code

        try:
            reason_map = await CancellationPolicyService.get_reason_map(
                session,
                owner_id,
                include_inactive=True,
                include_hidden=True,
            )
            reason = reason_map.get(reason_code)
            if isinstance(reason, CancellationReason):
                return reason.title
        except Exception as exc:
            logger.warning(
                "Failed to load cancellation reason title",
                owner_id=owner_id,
                reason_code=reason_code,
                error=str(exc),
            )
        return reason_code

    def _format_shift_window(
        self,
        start: Optional[datetime],
        end: Optional[datetime],
        timezone_str: Optional[str],
    ) -> str:
        local_start = timezone_helper.utc_to_local(start, timezone_str) if start else None
        local_end = timezone_helper.utc_to_local(end, timezone_str) if end else None
        if local_start and local_end:
            if local_start.date() == local_end.date():
                return f"{local_start.strftime('%d.%m.%Y %H:%M')} – {local_end.strftime('%H:%M')}"
            return f"{local_start.strftime('%d.%m.%Y %H:%M')} – {local_end.strftime('%d.%m.%Y %H:%M')}"
        if local_start:
            return local_start.strftime("%d.%m.%Y %H:%M")
        return "Неизвестно"

    async def _get_managers_for_object(
        self,
        session,
        object_id: int,
    ) -> List[int]:
        """Получить список user_id управляющих, имеющих доступ к объекту."""
        try:
            permission_service = ManagerPermissionService(session)
            permissions = await permission_service.get_object_permissions(object_id)
            
            manager_user_ids: List[int] = []
            for permission in permissions:
                # Проверяем, что у управляющего есть хотя бы одно право
                if not permission.has_any_permission():
                    continue
                
                # Получаем договор управляющего
                if not permission.contract:
                    continue
                
                # Проверяем, что договор активен
                if not permission.contract.is_active:
                    continue
                
                # employee_id в договоре управляющего - это user_id управляющего
                manager_user_ids.append(permission.contract.employee_id)
            
            # Убираем дубликаты
            return list(set(manager_user_ids))
            
        except Exception as exc:
            logger.error(
                "Failed to get managers for object",
                object_id=object_id,
                error=str(exc),
            )
            return []

    async def notify_shift_did_not_start(self, schedule_id: int) -> bool:
        """Уведомить владельца о том, что смена не состоялась."""
        async with get_async_session() as session:
            schedule = await self._load_schedule(session, schedule_id)
            if not schedule or not schedule.object or not schedule.object.owner:
                return False

            owner_id = schedule.object.owner_id
            if not owner_id:
                return False

            channels = await self._get_channels(owner_id, NotificationType.SHIFT_DID_NOT_START)
            if not channels:
                return False

            employee_name = self._build_user_name(schedule.user.first_name, schedule.user.last_name, schedule.user.username) if schedule.user else "Неизвестный сотрудник"
            shift_window = self._format_shift_window(schedule.planned_start, schedule.planned_end, schedule.object.timezone)

            data = {
                "shift_schedule_id": str(schedule.id),
                "object_id": str(schedule.object_id),
                "object_name": schedule.object.name,
                "employee_id": str(schedule.user_id) if schedule.user else None,
                "employee_name": employee_name,
                "shift_time": shift_window,
            }

            try:
                # Используем шаблоны через _send (title и message будут None, шаблоны подставятся автоматически)
                await self._send(owner_id, NotificationType.SHIFT_DID_NOT_START, channels, None, None, data, priority=NotificationPriority.HIGH)
                
                # Отправляем уведомления управляющим
                manager_user_ids = await self._get_managers_for_object(session, schedule.object_id)
                for manager_user_id in manager_user_ids:
                    try:
                        manager_channels = await self._get_channels(manager_user_id, NotificationType.SHIFT_DID_NOT_START)
                        if manager_channels:
                            await self._send(manager_user_id, NotificationType.SHIFT_DID_NOT_START, manager_channels, None, None, data, priority=NotificationPriority.HIGH)
                    except Exception as manager_exc:
                        logger.error(
                            "Failed to send shift did not start notification to manager",
                            manager_id=manager_user_id,
                            schedule_id=schedule_id,
                            error=str(manager_exc),
                        )
                
                return True
            except Exception as exc:
                logger.error(
                    "Failed to send shift did not start notification",
                    owner_id=owner_id,
                    schedule_id=schedule_id,
                    error=str(exc),
                )
                return False

    def _build_user_name(self, first: Optional[str], last: Optional[str], username: Optional[str]) -> str:
        parts = [part for part in [last, first] if part]
        if parts:
            return " ".join(parts)
        if username:
            return username
        return "Сотрудник"

