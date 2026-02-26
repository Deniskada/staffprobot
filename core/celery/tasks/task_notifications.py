"""Экстренные уведомления о новых задачах (Tasks v2) для активной смены.

Назначение: сразу после создания плана и генерации TaskEntryV2 уведомить сотрудников
в Telegram, чтобы они открыли «📝 Мои задачи» и увидели новые пункты.
"""

from __future__ import annotations

from typing import Iterable
from datetime import datetime, time, timezone, date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.celery.celery_app import celery_app
from core.database.session import get_celery_session
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


@celery_app.task(name="check_overdue_tasks")
def check_overdue_tasks() -> dict:
    """Проверить просроченные задачи и отправить уведомления.
    
    Логика:
    - Находит невыполненные TaskEntryV2 с дедлайном (deadline_time из плана)
    - Проверяет, просрочены ли они (deadline_time < current_time для сегодняшнего дня)
    - Отправляет уведомления сотруднику и владельцу через NotificationService
    
    Returns:
        dict: {"checked": int, "overdue": int, "notifications_sent": int}
    """
    import asyncio
    
    async def _check_overdue() -> dict:
        async with get_celery_session() as session:
            from domain.entities.task_entry import TaskEntryV2
            from domain.entities.task_plan import TaskPlanV2
            from domain.entities.shift import Shift
            from domain.entities.user import User
            from domain.entities.object import Object
            from shared.services.notification_service import NotificationService
            from domain.entities.notification import (
                NotificationType,
                NotificationChannel,
                NotificationPriority,
            )
            from core.celery.tasks.notification_tasks import send_notification_now
            
            now = datetime.now(timezone.utc)
            today = date.today()
            current_time = now.time()
            
            # Находим невыполненные задачи с планом, у которого есть дедлайн
            query = select(TaskEntryV2).where(
                and_(
                    TaskEntryV2.is_completed == False,
                    TaskEntryV2.plan_id.isnot(None)
                )
            ).options(
                selectinload(TaskEntryV2.plan),
                selectinload(TaskEntryV2.shift),
                selectinload(TaskEntryV2.employee)
            )
            
            result = await session.execute(query)
            entries = result.scalars().all()
            
            checked_count = len(entries)
            overdue_count = 0
            notifications_sent = 0
            
            notification_service = NotificationService()
            
            for entry in entries:
                if not entry.plan or not entry.plan.planned_time_start:
                    continue
                
                # Проверяем, просрочена ли задача
                deadline_time = entry.plan.planned_time_start
                
                # Определяем дату дедлайна на основе смены
                # Если есть смена и она началась - используем дату начала смены
                # Иначе используем сегодняшнюю дату
                deadline_date = today
                if entry.shift and entry.shift.start_time:
                    deadline_date = entry.shift.start_time.date()
                
                # Формируем datetime дедлайна
                from datetime import timezone as tz
                deadline_datetime = datetime.combine(deadline_date, deadline_time).replace(tzinfo=tz.utc)
                
                # Если текущее время больше дедлайна - задача просрочена
                if now > deadline_datetime:
                    overdue_count += 1
                    
                    # Получаем смену и объект для отправки уведомлений
                    shift = entry.shift
                    employee = entry.employee
                    
                    if not shift or not employee:
                        continue
                    
                    # Загружаем объект и владельца
                    object_query = select(Object).where(Object.id == shift.object_id)
                    object_result = await session.execute(object_query)
                    obj = object_result.scalar_one_or_none()
                    
                    if not obj:
                        continue
                    
                    owner_query = select(User).where(User.id == obj.owner_id)
                    owner_result = await session.execute(owner_query)
                    owner = owner_result.scalar_one_or_none()
                    
                    # Отправляем уведомление сотруднику
                    try:
                        deadline_str = deadline_time.strftime('%H:%M')
                        from domain.entities.task_template import TaskTemplateV2
                        template = await session.get(TaskTemplateV2, entry.template_id) if entry.template_id else None
                        task_title = template.title if template else "Задача"
                        
                        # Уведомление сотруднику
                        n_employee = await notification_service.create_notification(
                            user_id=employee.id,
                            type=NotificationType.TASK_OVERDUE,
                            channel=NotificationChannel.TELEGRAM,
                            title="⚠️ Задача просрочена",
                            message=(
                                f"Задача «{task_title}» просрочена.\n\n"
                                f"🕐 Дедлайн: {deadline_str}\n"
                                f"📍 Объект: {obj.name}\n\n"
                                f"Пожалуйста, выполните задачу как можно скорее."
                            ),
                            data={
                                "entry_id": entry.id,
                                "plan_id": entry.plan_id,
                                "shift_id": shift.id,
                                "object_id": obj.id
                            },
                            priority=NotificationPriority.HIGH,
                            scheduled_at=None
                        )
                        
                        if n_employee and getattr(n_employee, "id", None):
                            send_notification_now.apply_async(args=[int(n_employee.id)], queue="notifications")
                            notifications_sent += 1
                        
                        # Уведомление владельцу (если есть настройки уведомлений)
                        if owner:
                            # TODO: Проверить настройки уведомлений владельца на /owner/notifications
                            # Пока отправляем всегда
                            n_owner = await notification_service.create_notification(
                                user_id=owner.id,
                                type=NotificationType.TASK_OVERDUE,
                                channel=NotificationChannel.TELEGRAM,
                                title="⚠️ Просрочена задача сотрудника",
                                message=(
                                    f"Сотрудник {employee.full_name or employee.telegram_id} не выполнил задачу вовремя.\n\n"
                                    f"📋 Задача: «{task_title}»\n"
                                    f"🕐 Дедлайн: {deadline_str}\n"
                                    f"📍 Объект: {obj.name}\n"
                                    f"👤 Сотрудник: {employee.full_name or f'ID {employee.telegram_id}'}"
                                ),
                                data={
                                    "entry_id": entry.id,
                                    "plan_id": entry.plan_id,
                                    "shift_id": shift.id,
                                    "employee_id": employee.id,
                                    "object_id": obj.id
                                },
                                priority=NotificationPriority.HIGH,
                                scheduled_at=None
                            )
                            
                            if n_owner and getattr(n_owner, "id", None):
                                send_notification_now.apply_async(args=[int(n_owner.id)], queue="notifications")
                                notifications_sent += 1
                        
                        logger.info(
                            "Overdue task notification created",
                            entry_id=entry.id,
                            employee_id=employee.id,
                            owner_id=owner.id if owner else None,
                            deadline=deadline_str
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to create overdue task notification",
                            entry_id=entry.id,
                            error=str(e),
                            exc_info=True
                        )
            
            return {
                "checked": checked_count,
                "overdue": overdue_count,
                "notifications_sent": notifications_sent
            }
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если event loop уже запущен, создаем новый
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _check_overdue())
                return future.result()
        else:
            return asyncio.run(_check_overdue())
    except Exception as e:
        logger.error("check_overdue_tasks failed", error=str(e), exc_info=True)
        return {"checked": 0, "overdue": 0, "notifications_sent": 0, "error": str(e)}


