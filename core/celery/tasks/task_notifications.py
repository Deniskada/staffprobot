"""Экстренные уведомления о новых задачах (Tasks v2) для активной смены.

Назначение: сразу после создания плана и генерации TaskEntryV2 уведомить сотрудников
в Telegram, чтобы они открыли «📝 Мои задачи» и увидели новые пункты.
"""

from __future__ import annotations

from typing import Iterable

from core.celery.celery_app import celery_app
from core.logging.logger import logger


@celery_app.task(name="notify_tasks_updated")
def notify_tasks_updated(employee_ids: list[int] | tuple[int, ...]) -> int:
    """Отправить сотрудникам сервисное сообщение о новых задачах.

    Args:
        employee_ids: список внутренних user_id сотрудников

    Returns:
        Количество успешно инициированных отправок
    """
    try:
        from core.database.session import get_sync_session
        from sqlalchemy import select
        from domain.entities.user import User
        from shared.services.senders.telegram_sender import get_telegram_sender
        from domain.entities.notification import (
            Notification,
            NotificationType,
            NotificationChannel,
            NotificationPriority,
        )

        if not employee_ids:
            return 0

        session = get_sync_session()
        try:
            # Загружаем пользователей и их telegram_id
            result = session.execute(select(User).where(User.id.in_(list(employee_ids))))
            users: Iterable[User] = result.scalars().all()

            sender = get_telegram_sender()
            sent_count = 0

            for u in users:
                if not u.telegram_id:
                    logger.info("Skip notify: user has no telegram_id", user_id=u.id)
                    continue

                # Готовим простое сообщение без использования шаблонов
                notification = Notification(
                    user_id=u.id,
                    type=NotificationType.FEATURE_ANNOUNCEMENT,
                    channel=NotificationChannel.TELEGRAM,
                    priority=NotificationPriority.NORMAL,
                    title="Новая задача",
                    message=(
                        "Вам назначена новая задача по текущей смене.\n\n"
                        "Откройте ‘📝 Мои задачи’, чтобы посмотреть список."
                    ),
                )
                text = "📋 Новая задача назначена. Откройте ‘📝 Мои задачи’, чтобы посмотреть список."

                # Отправляем в Telegram, минуя шаблонизатор уведомлений
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(sender._send_with_retry(
                        telegram_id=int(u.telegram_id),
                        message=text,
                        parse_mode="HTML",
                        notification=notification
                    ))
                    if success:
                        sent_count += 1
                finally:
                    loop.close()

            logger.info("Tasks updated notifications sent", total=sent_count)
            return sent_count
        finally:
            session.close()
    except Exception as e:
        logger.error("notify_tasks_updated failed", error=str(e))
        return 0


