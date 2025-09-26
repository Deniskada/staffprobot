"""Общий сервис уведомлений (web + Telegram)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.logging.logger import logger
from domain.entities.notification import Notification
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.user import User
from shared.services.role_based_login_service import RoleBasedLoginService
from shared.services.manager_permission_service import ManagerPermissionService

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:  # pragma: no cover
    Bot = None  # type: ignore
    TelegramError = Exception  # type: ignore


class NotificationService:
    """Сервис для создания веб-уведомлений и отправки Telegram сообщений."""

    def __init__(self, session: Session, telegram_token: Optional[str] = None):
        self.session = session
        self.telegram_token = telegram_token
        self.bot: Optional[Bot] = None
        if telegram_token and Bot:
            try:
                self.bot = Bot(token=telegram_token)
            except Exception:  # pragma: no cover
                logger.exception("Не удалось инициализировать Telegram Bot")
                self.bot = None

    # ------------------------------------------------------------------
    # Общие методы
    # ------------------------------------------------------------------
    def create(
        self,
        user_ids: Sequence[int],
        notification_type: str,
        payload: Dict[str, Any],
        channel: str = "web",
        source: str = "system",
        send_telegram: bool = True,
    ) -> List[Notification]:
        now = datetime.now(timezone.utc)
        notifications: List[Notification] = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                payload=payload,
                channel=channel,
                source=source,
                created_at=now,
                is_read=False,
            )
            self.session.add(notification)
            notifications.append(notification)
        self.session.flush()

        if send_telegram:
            self._send_telegram_notifications(notifications)

        return notifications

    def _send_telegram_notifications(self, notifications: Iterable[Notification]) -> None:
        if not self.bot:
            return

        user_ids = {item.user_id for item in notifications}
        if not user_ids:
            return

        result = self.session.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {user.id: user for user in result.scalars()}

        for notification in notifications:
            user = users_map.get(notification.user_id)
            if not user or not user.telegram_id:
                continue

            try:
                message = self._format_telegram_message(notification)
                if not message:
                    continue

                self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode="HTML",
                )
            except TelegramError:  # pragma: no cover
                logger.exception(
                    "Не удалось отправить Telegram уведомление пользователю %s",
                    user.telegram_id,
                )

    def _format_telegram_message(self, notification: Notification) -> Optional[str]:
        payload = notification.payload or {}
        status = notification.type

        if status == "application_created":
            return (
                "📄 <b>Новая заявка</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Соискатель: <b>{payload.get('applicant_name', '—')}</b>"
            )
        if status == "application_approved":
            return (
                "✅ <b>Заявка одобрена</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>"
            )
        if status == "application_rejected":
            return (
                "❌ <b>Заявка отклонена</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Причина: {payload.get('reason', '—')}"
            )
        if status == "interview_assigned":
            return (
                "📅 <b>Назначено собеседование</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Дата: {payload.get('scheduled_at', '—')}"
            )
        if status == "interview_cancelled":
            return (
                "⚠️ <b>Собеседование отменено</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Причина: {payload.get('reason', '—')}"
            )
        if status == "interview_reminder":
            return (
                "⏰ <b>Напоминание о собеседовании</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Начало через: {payload.get('time_until', '—')}"
            )
        if status == "shift_reminder":
            return (
                "⏰ <b>Напоминание о смене</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Время: {payload.get('time_range', '—')}"
            )
        if status == "shift_cancelled":
            return (
                "❌ <b>Смена отменена</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Время: {payload.get('time_range', '—')}"
            )
        if status == "shift_confirmed":
            return (
                "✅ <b>Смена подтверждена</b>\n\n"
                f"Объект: <b>{payload.get('object_name', '—')}</b>\n"
                f"Время: {payload.get('time_range', '—')}\n"
                f"Оплата: {payload.get('payment', '—')}"
            )
        return None

    def get_unread(self, user_id: int, limit: int = 20) -> List[Notification]:
        result = self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    def mark_as_read(self, user_id: int, notification_ids: Sequence[int]) -> None:
        if not notification_ids:
            return
        self.session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.id.in_(notification_ids))
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )

    def create_for_role(
        self,
        role: str,
        notification_type: str,
        payload: Dict[str, Any],
        **kwargs: Any,
    ) -> List[Notification]:
        login_service = RoleBasedLoginService(self.session)
        user_ids = login_service.get_user_ids_by_role(role)
        if not user_ids:
            return []
        return self.create(user_ids, notification_type, payload, **kwargs)

    def create_for_object_managers(
        self,
        object_id: int,
        notification_type: str,
        payload: Dict[str, Any],
        **kwargs: Any,
    ) -> List[Notification]:
        permission_service = ManagerPermissionService(self.session)
        manager_ids = permission_service.get_manager_user_ids_for_object(object_id)
        if not manager_ids:
            return []
        return self.create(manager_ids, notification_type, payload, **kwargs)

    # ------------------------------------------------------------------
    # Работа со сменами
    # ------------------------------------------------------------------
    def get_shifts_for_reminder(self, hours_before: int = 2) -> List[ShiftSchedule]:
        now = datetime.now(timezone.utc)
        reminder_time = now + timedelta(hours=hours_before)
        query = (
            select(ShiftSchedule)
            .where(
                ShiftSchedule.status.in_(["planned", "confirmed"]),
                ShiftSchedule.notification_sent.is_(False),
                ShiftSchedule.planned_start <= reminder_time,
                ShiftSchedule.planned_start > now,
            )
            .order_by(ShiftSchedule.planned_start)
        )
        result = self.session.execute(query)
        return list(result.scalars())

    def mark_reminder_sent(self, schedule_id: int) -> None:
        self.session.execute(
            update(ShiftSchedule)
            .where(ShiftSchedule.id == schedule_id)
            .values(notification_sent=True)
        )

    def send_shift_reminder(
        self,
        schedule: ShiftSchedule,
        send_telegram: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "object_name": schedule.object.name if schedule.object else "—",
            "time_range": schedule.formatted_time_range,
        }
        self.create([schedule.user_id], "shift_reminder", payload, send_telegram=send_telegram)
        self.mark_reminder_sent(schedule.id)
        return payload

    def send_shift_cancelled(self, schedule: ShiftSchedule, send_telegram: bool = True) -> Dict[str, Any]:
        payload = {
            "object_name": schedule.object.name if schedule.object else "—",
            "time_range": schedule.formatted_time_range,
        }
        self.create([schedule.user_id], "shift_cancelled", payload, send_telegram=send_telegram)
        return payload

    def send_shift_confirmed(
        self,
        schedule: ShiftSchedule,
        payment: Optional[float] = None,
        send_telegram: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "object_name": schedule.object.name if schedule.object else "—",
            "time_range": schedule.formatted_time_range,
            "payment": f"{payment:.2f} ₽" if payment is not None else "—",
        }
        self.create([schedule.user_id], "shift_confirmed", payload, send_telegram=send_telegram)
        return payload

    def process_pending_reminders(
        self,
        hours_before: int = 2,
    ) -> Dict[str, Any]:
        """Обработка всех ожидающих напоминаний."""
        shifts = self.get_shifts_for_reminder(hours_before)
        
        result = {
            "total_shifts": len(shifts),
            "sent_successfully": 0,
            "failed_to_send": 0,
            "errors": []
        }
        
        for shift in shifts:
            try:
                self.send_shift_reminder(shift, send_telegram=True)
                result["sent_successfully"] += 1
            except Exception as e:
                logger.error(f"Failed to send reminder for shift {shift.id}: {e}")
                result["failed_to_send"] += 1
                result["errors"].append(f"Shift {shift.id}: {str(e)}")
        
        return result