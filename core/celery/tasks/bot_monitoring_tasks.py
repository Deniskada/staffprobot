"""Celery задачи мониторинга Telegram-бота."""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import select, or_

from core.celery.celery_app import celery_app
from core.cache.redis_cache import cache
from core.logging.logger import logger
from core.database.session import get_celery_session
from domain.entities.user import User, UserRole
from domain.entities.notification import (
    NotificationType,
    NotificationChannel,
    NotificationPriority,
)
from shared.services.notification_service import NotificationService

LOCK_KEY = "bot_polling_lock"
HEARTBEAT_KEY = "bot_polling_heartbeat"
ALERT_SENT_KEY = "bot_polling_alert_sent"
HEARTBEAT_TIMEOUT = timedelta(minutes=5)
ALERT_TTL_SECONDS = 5 * 60


@celery_app.task(name="monitor_bot_heartbeat")
def monitor_bot_heartbeat() -> None:
    """Проверка heartbeat Telegram-бота."""
    try:
        asyncio.run(_monitor_bot_heartbeat())
    except Exception as exc:
        logger.error("monitor_bot_heartbeat failed", exc_info=exc)


async def _monitor_bot_heartbeat() -> None:
    if not cache.is_connected:
        await cache.connect()
    redis = cache.redis
    heartbeat_raw = await redis.get(HEARTBEAT_KEY)
    alert_sent = await redis.get(ALERT_SENT_KEY)
    now = datetime.now(timezone.utc)

    payload: Optional[dict] = None
    heartbeat_dt: Optional[datetime] = None
    if heartbeat_raw:
        try:
            payload = json.loads(heartbeat_raw.decode("utf-8"))
            ts = payload.get("ts")
            if ts:
                heartbeat_dt = datetime.fromisoformat(ts)
        except Exception as exc:
            logger.warning("Failed to parse bot heartbeat payload", exc_info=exc)
            heartbeat_dt = None

    is_stale = (
        not heartbeat_dt or (now - heartbeat_dt) > HEARTBEAT_TIMEOUT
    )

    if is_stale:
        age_seconds = None
        if heartbeat_dt:
            age_seconds = (now - heartbeat_dt).total_seconds()
        logger.error(
            "Bot heartbeat missing or stale",
            extra={
                "payload": payload,
                "age_seconds": age_seconds,
            },
        )
        if not alert_sent:
            await _send_bot_alert(payload, age_seconds)
            await redis.set(ALERT_SENT_KEY, "1", ex=ALERT_TTL_SECONDS)
    else:
        if alert_sent:
            await redis.delete(ALERT_SENT_KEY)
            logger.info("Bot heartbeat restored", extra={"payload": payload})


async def _send_bot_alert(payload: Optional[dict], age_seconds: Optional[float]) -> None:
    """Отправка уведомлений суперадминам / DevOps."""
    async with get_celery_session() as session:
        superadmin_ids = await _get_superadmin_ids(session)

    if not superadmin_ids:
        logger.warning("No superadmin users found for bot alert")
        return

    lock_info = json.dumps(payload or {}, ensure_ascii=False)
    age_text = f"{age_seconds:.0f} сек." if age_seconds is not None else "неизвестно"
    title = "⚠️ Telegram бот не отвечает"
    message = (
        "Система не получает heartbeat от Telegram-бота.\n\n"
        f"Последний lock: {lock_info}\n"
        f"Возраст heartbeat: {age_text}\n\n"
        "Проверьте сервис `bot` и очередь обновлений."
    )

    notification_service = NotificationService()
    for user_id in superadmin_ids:
        await notification_service.create_notification(
            user_id=user_id,
            type=NotificationType.SYSTEM_MAINTENANCE,
            channel=NotificationChannel.IN_APP,
            title=title,
            message=message,
            priority=NotificationPriority.URGENT,
        )
        await notification_service.create_notification(
            user_id=user_id,
            type=NotificationType.SYSTEM_MAINTENANCE,
            channel=NotificationChannel.TELEGRAM,
            title=title,
            message=message,
            priority=NotificationPriority.URGENT,
        )


async def _get_superadmin_ids(session) -> List[int]:
    roles_filter = User.roles.contains([UserRole.SUPERADMIN.value])
    query = select(User.id).where(
        or_(User.role == UserRole.SUPERADMIN.value, roles_filter),
        User.is_active.is_(True),
    )
    result = await session.execute(query)
    return [row[0] for row in result.all()]

