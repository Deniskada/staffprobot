"""Celery задачи для уведомлений (универсальные)."""

import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from celery import Task

from core.celery.celery_app import celery_app
from core.logging.logger import logger


class NotificationTask(Task):
    """Базовый класс для задач уведомлений."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            f"Notification task failed: {self.name} (task_id: {task_id}, error: {str(exc)})"
        )

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            f"Notification task completed: {self.name} (task_id: {task_id})"
        )


async def _dispatch_all_scheduled():
    """Получить pending-уведомления и отправить через соответствующие каналы.

    Использует get_celery_session (NullPool) — безопасно для asyncio.run().
    """
    from core.database.session import get_celery_session
    from domain.entities.notification import (
        Notification, NotificationChannel, NotificationStatus,
    )
    from domain.entities.user import User
    from shared.services.senders.telegram_sender import get_telegram_sender
    from shared.templates.notifications.base_templates import NotificationTemplateManager
    from sqlalchemy import select, text, and_, cast, String

    stats: Dict[str, int] = {"processed": 0, "sent": 0, "failed": 0}

    async with get_celery_session() as session:
        now = datetime.now(timezone.utc)

        rows = await session.execute(
            select(Notification).where(
                and_(
                    cast(Notification.status, String) == NotificationStatus.PENDING.value,
                    Notification.scheduled_at <= now,
                )
            ).order_by(Notification.scheduled_at)
        )
        notifications = list(rows.scalars().all())
        stats["processed"] = len(notifications)

        if not notifications:
            return stats

        user_ids = {n.user_id for n in notifications}
        user_rows = await session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users_map = {u.id: u for u in user_rows.scalars().all()}

        tg_sender = get_telegram_sender()

        for notif in notifications:
            try:
                user = users_map.get(notif.user_id)
                if not user:
                    logger.warning(f"User {notif.user_id} not found for notification {notif.id}")
                    await _mark(session, notif.id, "failed", error="User not found")
                    stats["failed"] += 1
                    continue

                channel = notif.channel_enum
                success = False

                if channel == NotificationChannel.TELEGRAM:
                    if not user.telegram_id:
                        logger.warning(f"User {user.id} has no telegram_id")
                        await _mark(session, notif.id, "failed", error="No telegram_id")
                        stats["failed"] += 1
                        continue
                    success = await tg_sender.send_notification(
                        notification=notif,
                        telegram_id=user.telegram_id,
                        variables=notif.data,
                    )
                elif channel == NotificationChannel.IN_APP:
                    success = True
                else:
                    logger.warning(f"Unsupported channel {notif.channel} for notification {notif.id}")
                    success = False

                if success:
                    await _mark(session, notif.id, "sent")
                    stats["sent"] += 1
                else:
                    await _mark(session, notif.id, "failed", error="Send failed")
                    stats["failed"] += 1

            except Exception as e:
                logger.error(f"Error dispatching notification {notif.id}: {e}")
                try:
                    await session.rollback()
                    await _mark(session, notif.id, "failed", error=str(e)[:200])
                except Exception:
                    pass
                stats["failed"] += 1

    logger.info("Scheduled notifications dispatched", **stats)
    return stats


async def _mark(session, notif_id: int, status: str, error: str | None = None):
    """Обновить статус уведомления через raw SQL (в той же celery-сессии)."""
    from sqlalchemy import text
    now = datetime.now(timezone.utc)

    await session.execute(
        text("UPDATE notifications SET status = :status WHERE id = :id"),
        {"status": status, "id": notif_id},
    )
    if status == "sent":
        await session.execute(
            text("UPDATE notifications SET sent_at = :ts WHERE id = :id"),
            {"ts": now, "id": notif_id},
        )
    if error:
        await session.execute(
            text("UPDATE notifications SET error_message = :err, retry_count = retry_count + 1 WHERE id = :id"),
            {"err": error, "id": notif_id},
        )
    await session.commit()


@celery_app.task(base=NotificationTask, name="send_notification_now")
def send_notification_now(notification_id: int) -> bool:
    """Отправить одно уведомление по ID."""
    try:
        return asyncio.run(_dispatch_single(notification_id))
    except Exception as e:
        logger.error("send_notification_now failed", notification_id=notification_id, error=str(e))
        return False


async def _dispatch_single(notification_id: int) -> bool:
    """Отправить одно уведомление (Celery-safe сессия)."""
    from core.database.session import get_celery_session
    from domain.entities.notification import Notification, NotificationChannel, NotificationStatus
    from domain.entities.user import User
    from shared.services.senders.telegram_sender import get_telegram_sender
    from sqlalchemy import select, cast, String

    async with get_celery_session() as session:
        row = await session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notif = row.scalar_one_or_none()
        if not notif or notif.status_enum != NotificationStatus.PENDING:
            return False

        user_row = await session.execute(select(User).where(User.id == notif.user_id))
        user = user_row.scalar_one_or_none()
        if not user:
            await _mark(session, notification_id, "failed", error="User not found")
            return False

        success = False
        if notif.channel_enum == NotificationChannel.TELEGRAM:
            if not user.telegram_id:
                await _mark(session, notification_id, "failed", error="No telegram_id")
                return False
            tg_sender = get_telegram_sender()
            success = await tg_sender.send_notification(
                notification=notif, telegram_id=user.telegram_id, variables=notif.data
            )
        elif notif.channel_enum == NotificationChannel.IN_APP:
            success = True

        await _mark(session, notification_id, "sent" if success else "failed",
                     error=None if success else "Send failed")
        return success


@celery_app.task(base=NotificationTask, name="dispatch_scheduled_notifications")
def dispatch_scheduled_notifications() -> Dict[str, Any]:
    """Обработать и отправить все запланированные уведомления (scheduled <= now)."""
    try:
        return asyncio.run(_dispatch_all_scheduled())
    except Exception as e:
        logger.error("dispatch_scheduled_notifications failed", error=str(e))
        return {"processed": 0, "sent": 0, "failed": 0, "error": str(e)}


@celery_app.task(base=NotificationTask, bind=True)
def process_reminders(self):
    """Совместимая задача: делегирует на обработку запланированных уведомлений."""
    try:
        return dispatch_scheduled_notifications()
    except Exception as e:
        logger.error("process_reminders failed", error=str(e))
        raise
