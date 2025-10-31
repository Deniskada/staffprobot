"""Celery задачи для создания напоминаний о сменах и объектах."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from celery import Task
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from core.celery.celery_app import celery_app
from core.logging.logger import logger
from core.database.session import get_async_session
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift
from domain.entities.notification import Notification, NotificationType, NotificationChannel, NotificationPriority
from domain.entities.user import User
from domain.entities.object import Object


class ReminderTask(Task):
    """Базовый класс для задач напоминаний."""
    
    name = "ReminderTask"
    max_retries = 3
    default_retry_delay = 60


@celery_app.task(base=ReminderTask, bind=True, name="create_shift_reminders")
def create_shift_reminders(self) -> Dict[str, Any]:
    """
    Создать уведомления SHIFT_REMINDER для смен начинающихся через 1 час.
    Запускается каждые 5 минут.
    
    Returns:
        Статистика: сколько уведомлений создано
    """
    try:
        import asyncio
        return asyncio.run(_create_shift_reminders_async())
    except Exception as e:
        logger.error(f"create_shift_reminders failed: {e}")
        raise


async def _create_shift_reminders_async() -> Dict[str, Any]:
    """Асинхронная логика создания напоминаний о сменах."""
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    try:
        async with get_async_session() as session:
            # Время проверки: через 1 час (±5 минут для покрытия интервала запуска)
            # ВРЕМЕННО: расширенное окно для тестирования
            now = datetime.now(timezone.utc)
            target_time_start = now + timedelta(minutes=25)  # 25 минут (для теста)
            target_time_end = now + timedelta(minutes=65)    # 65 минут
            
            # Найти запланированные смены (shift_schedules) начинающиеся через ~1 час
            query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.user),
                selectinload(ShiftSchedule.object)
            ).where(
                and_(
                    ShiftSchedule.planned_start >= target_time_start,
                    ShiftSchedule.planned_start <= target_time_end,
                    ShiftSchedule.status.in_(["planned", "confirmed"])
                )
            )
            
            result = await session.execute(query)
            upcoming_shifts = result.scalars().all()
            
            logger.info(
                f"Found {len(upcoming_shifts)} shifts starting in ~1 hour",
                target_range=f"{target_time_start} - {target_time_end}"
            )
            
            for shift_schedule in upcoming_shifts:
                try:
                    user = shift_schedule.user
                    if not user:
                        logger.warning(f"ShiftSchedule {shift_schedule.id} has no user")
                        skipped_count += 1
                        continue
                    
                    # Проверить настройки уведомлений пользователя
                    prefs = user.notification_preferences or {}
                    shift_reminder_prefs = prefs.get("shift_reminder", {})
                    
                    # Проверить включены ли уведомления
                    telegram_enabled = shift_reminder_prefs.get("telegram", True)
                    inapp_enabled = shift_reminder_prefs.get("inapp", True)
                    
                    if not telegram_enabled and not inapp_enabled:
                        logger.debug(
                            f"User {user.id} disabled shift_reminder notifications",
                            shift_schedule_id=shift_schedule.id
                        )
                        skipped_count += 1
                        continue
                    
                    # Проверить не создано ли уже уведомление для этой смены
                    from sqlalchemy import cast, String
                    existing_query = select(Notification).where(
                        and_(
                            Notification.user_id == user.id,
                            Notification.type == NotificationType.SHIFT_REMINDER,
                            cast(Notification.data['shift_schedule_id'], String) == str(shift_schedule.id)
                        )
                    )
                    existing_result = await session.execute(existing_query)
                    existing_notification = existing_result.scalar_one_or_none()
                    
                    if existing_notification:
                        logger.debug(
                            f"Notification already exists for shift_schedule {shift_schedule.id}",
                            notification_id=existing_notification.id
                        )
                        skipped_count += 1
                        continue
                    
                    # Формируем данные для шаблона
                    obj = shift_schedule.object
                    object_name = obj.name if obj else "Неизвестный объект"
                    object_address = obj.address if obj else ""
                    
                    # Локальное время для отображения
                    from core.utils.timezone_helper import timezone_helper
                    local_start = timezone_helper.utc_to_local(shift_schedule.planned_start)
                    local_end = timezone_helper.utc_to_local(shift_schedule.planned_end)
                    shift_time = f"{local_start.strftime('%H:%M')} - {local_end.strftime('%H:%M')}"
                    
                    # Создать уведомления для включённых каналов
                    if telegram_enabled:
                        notification_tg = Notification(
                            user_id=user.id,
                            type=NotificationType.SHIFT_REMINDER,
                            channel=NotificationChannel.TELEGRAM,
                            priority=NotificationPriority.HIGH,
                            title="Напоминание о смене",
                            message=f"Привет, {user.first_name}!\n\nНапоминаем, что ваша смена начинается через 1 час на объекте '{object_name}'.\n\nВремя смены: {shift_time}\nАдрес: {object_address}\n\nНе забудьте отметиться по геолокации!",
                            data={
                                "shift_schedule_id": shift_schedule.id,
                                "object_id": shift_schedule.object_id,
                                "object_name": object_name,
                                "shift_time": shift_time,
                                "time_until": "1 час"
                            },
                            scheduled_at=now  # Отправить сразу
                        )
                        session.add(notification_tg)
                        created_count += 1
                    
                    if inapp_enabled:
                        notification_inapp = Notification(
                            user_id=user.id,
                            type=NotificationType.SHIFT_REMINDER,
                            channel=NotificationChannel.IN_APP,
                            priority=NotificationPriority.HIGH,
                            title="Напоминание о смене",
                            message=f"Ваша смена начинается через 1 час на объекте '{object_name}'",
                            data={
                                "shift_schedule_id": shift_schedule.id,
                                "object_id": shift_schedule.object_id,
                                "object_name": object_name,
                                "shift_time": shift_time,
                                "time_until": "1 час"
                            },
                            scheduled_at=now  # Отправить сразу
                        )
                        session.add(notification_inapp)
                        created_count += 1
                    
                    await session.commit()
                    
                    logger.info(
                        f"Created shift reminder for user {user.id}",
                        shift_schedule_id=shift_schedule.id,
                        telegram=telegram_enabled,
                        inapp=inapp_enabled
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error creating reminder for shift_schedule {shift_schedule.id}: {e}"
                    )
                    error_count += 1
                    continue
            
            result = {
                "created": created_count,
                "skipped": skipped_count,
                "errors": error_count,
                "total_shifts": len(upcoming_shifts)
            }
            
            logger.info(
                f"Shift reminders task completed: created={result['created']}, skipped={result['skipped']}, errors={result['errors']}, total_shifts={result['total_shifts']}"
            )
            
            return result
            
    except Exception as e:
        logger.error(f"Fatal error in _create_shift_reminders_async: {e}")
        return {"created": 0, "skipped": 0, "errors": 1, "total_shifts": 0, "error": str(e)}


@celery_app.task(base=ReminderTask, bind=True, name="check_object_openings")
def check_object_openings(self) -> Dict[str, Any]:
    """
    Проверка открытия/закрытия объектов.
    Запускается каждые 10 минут.
    
    Создает уведомления:
    - OBJECT_OPENED: объект открылся вовремя
    - OBJECT_LATE_OPENING: объект открылся с опозданием
    - OBJECT_NO_SHIFTS_TODAY: нет смен на объекте
    - OBJECT_EARLY_CLOSING: объект закрылся раньше
    - OBJECT_CLOSED: объект закрылся
    
    Returns:
        Статистика: сколько уведомлений создано
    """
    try:
        import asyncio
        return asyncio.run(_check_object_openings_async())
    except Exception as e:
        logger.error(f"check_object_openings failed: {e}")
        raise


async def _check_object_openings_async() -> Dict[str, Any]:
    """Асинхронная логика проверки открытия объектов."""
    stats = {
        "opened": 0,
        "late_opening": 0,
        "no_shifts": 0,
        "early_closing": 0,
        "closed": 0,
        "errors": 0
    }
    
    try:
        from core.utils.timezone_helper import timezone_helper
        
        # Текущее время
        now = datetime.now(timezone.utc)
        today_local = timezone_helper.utc_to_local(now).date()
        
        # Получить все активные объекты
        async with get_async_session() as session:
            query = select(Object).options(
                selectinload(Object.owner)
            ).where(Object.is_active == True)
            
            result = await session.execute(query)
            objects = list(result.scalars().all())
        
        # Обрабатываем каждый объект в отдельной транзакции
        for obj in objects:
            # Пропустить если нет владельца
            if not obj.owner_id:
                continue
            
            try:
                async with get_async_session() as session:
                    # Загружаем объект заново с owner в текущей сессии
                    obj_query = select(Object).options(
                        selectinload(Object.owner)
                    ).where(Object.id == current_obj.id)
                    obj_result = await session.execute(obj_query)
                    current_obj = obj_result.scalar_one_or_none()
                    
                    if not current_obj or not current_obj.owner:
                        continue
                    
                    # Получить смены объекта на сегодня
                    shifts_query = select(Shift).where(
                        and_(
                            Shift.object_id == current_obj.id,
                            Shift.planned_start >= timezone_helper.start_of_day_utc(today_local),
                            Shift.planned_start < timezone_helper.end_of_day_utc(today_local)
                        )
                    ).options(selectinload(Shift.user))
                    
                    shifts_result = await session.execute(shifts_query)
                    shifts_today = list(shifts_result.scalars().all())
                    
                    logger.info(f"Object {current_obj.id} ({current_obj.name}): {len(shifts_today)} shifts found, opening_time={current_obj.opening_time}, closing_time={current_obj.closing_time}")
                    
                    # Проверка 1: НЕТ СМЕН НА ОБЪЕКТЕ
                    if not shifts_today and current_obj.opening_time:
                        # Проверяем только один раз в день (например, после времени открытия)
                        expected_open_time = datetime.combine(today_local, current_obj.opening_time).replace(tzinfo=timezone_helper.local_tz)
                        if now >= expected_open_time.astimezone(timezone.utc):
                            # Проверить не создано ли уже уведомление
                            notification_exists = await _check_notification_exists(
                                session, current_obj.owner_id, NotificationType.OBJECT_NO_SHIFTS_TODAY.value, 
                                {"object_id": current_obj.id, "date": str(today_local)}
                            )
                            
                            if not notification_exists:
                                await _create_object_notification(
                                    session, obj, current_obj.owner, NotificationType.OBJECT_NO_SHIFTS_TODAY,
                                    {
                                        "object_name": current_obj.name,
                                        "object_address": current_obj.address or "",
                                        "date": today_local.strftime("%d.%m.%Y")
                                    },
                                    now
                                )
                                stats["no_shifts"] += 1
                        continue
                    
                    # Для объектов со сменами проверяем открытие/закрытие
                    if shifts_today and current_obj.opening_time and current_obj.closing_time:
                        logger.info(f"Checking object {current_obj.id} ({current_obj.name}): {len(shifts_today)} shifts today")
                        # Найти первую и последнюю смену
                        first_shift = min(shifts_today, key=lambda s: s.planned_start or s.start_time)
                        last_shift = max(shifts_today, key=lambda s: s.end_time or s.start_time)
                        logger.info(f"Object {current_obj.id}: first_shift={first_shift.id}, last_shift={last_shift.id}, last_status={last_shift.status}, last_end_time={last_shift.end_time}")
                        
                        # Проверка 2: ОТКРЫТИЕ ОБЪЕКТА (вовремя или с опозданием)
                        if first_shift.actual_start:
                            expected_open = datetime.combine(today_local, current_obj.opening_time).replace(tzinfo=timezone_helper.local_tz)
                            actual_open_local = timezone_helper.utc_to_local(first_shift.actual_start)
                            
                            delay_minutes = int((actual_open_local - expected_open).total_seconds() / 60)
                            
                            # Уже создавали уведомление?
                            notif_type = NotificationType.OBJECT_LATE_OPENING if delay_minutes > 5 else NotificationType.OBJECT_OPENED
                            notification_exists = await _check_notification_exists(
                                session, current_obj.owner_id, 
                                notif_type.value,  # Передаём строковое значение
                                {"object_id": current_obj.id, "shift_id": first_shift.id}
                            )
                            
                            if not notification_exists:
                                if delay_minutes > 5:  # Опоздание больше 5 минут
                                    await _create_object_notification(
                                        session, obj, current_obj.owner, NotificationType.OBJECT_LATE_OPENING,
                                        {
                                            "object_name": current_obj.name,
                                            "employee_name": f"{first_shift.user.first_name} {first_shift.user.last_name}" if first_shift.user else "Неизвестный",
                                            "planned_time": expected_open.strftime("%H:%M"),
                                            "actual_time": actual_open_local.strftime("%H:%M"),
                                            "delay_minutes": str(delay_minutes)
                                        },
                                        now
                                    )
                                    stats["late_opening"] += 1
                                else:  # Вовремя
                                    await _create_object_notification(
                                        session, obj, current_obj.owner, NotificationType.OBJECT_OPENED,
                                        {
                                            "object_name": current_obj.name,
                                            "employee_name": f"{first_shift.user.first_name} {first_shift.user.last_name}" if first_shift.user else "Неизвестный",
                                            "open_time": actual_open_local.strftime("%H:%M")
                                        },
                                        now
                                    )
                                    stats["opened"] += 1
                        
                        # Проверка 3: ЗАКРЫТИЕ ОБЪЕКТА (вовремя или раньше)
                        if last_shift.end_time and last_shift.status in ('completed', 'closed'):
                            expected_close = datetime.combine(today_local, current_obj.closing_time).replace(tzinfo=timezone_helper.local_tz)
                            actual_close_local = timezone_helper.utc_to_local(last_shift.end_time)
                            
                            early_minutes = int((expected_close - actual_close_local).total_seconds() / 60)
                            
                            # Уже создавали уведомление?
                            notif_type_close = NotificationType.OBJECT_EARLY_CLOSING if early_minutes > 5 else NotificationType.OBJECT_CLOSED
                            notification_exists = await _check_notification_exists(
                                session, current_obj.owner_id,
                                notif_type_close.value,  # Передаём строковое значение
                                {"object_id": current_obj.id, "shift_id": last_shift.id}
                            )
                            
                            if not notification_exists:
                                if early_minutes > 5:  # Раннее закрытие больше 5 минут
                                    await _create_object_notification(
                                        session, obj, current_obj.owner, NotificationType.OBJECT_EARLY_CLOSING,
                                        {
                                            "object_name": current_obj.name,
                                            "employee_name": f"{last_shift.user.first_name} {last_shift.user.last_name}" if last_shift.user else "Неизвестный",
                                            "planned_time": expected_close.strftime("%H:%M"),
                                            "actual_time": actual_close_local.strftime("%H:%M"),
                                            "early_minutes": str(early_minutes)
                                        },
                                        now
                                    )
                                    stats["early_closing"] += 1
                                else:  # Вовремя
                                    await _create_object_notification(
                                        session, obj, current_obj.owner, NotificationType.OBJECT_CLOSED,
                                        {
                                            "object_name": current_obj.name,
                                            "employee_name": f"{last_shift.user.first_name} {last_shift.user.last_name}" if last_shift.user else "Неизвестный",
                                            "close_time": actual_close_local.strftime("%H:%M")
                                        },
                                        now
                                    )
                                    stats["closed"] += 1
                    
            except Exception as e:
                logger.error(f"Error checking object {current_obj.id}: {e}")
                stats["errors"] += 1
                continue
        
        logger.info(f"Object openings check completed: opened={stats['opened']}, late_opening={stats['late_opening']}, no_shifts={stats['no_shifts']}, early_closing={stats['early_closing']}, closed={stats['closed']}, errors={stats['errors']}")
        return stats
            
    except Exception as e:
        logger.error(f"Fatal error in _check_object_openings_async: {e}")
        stats["errors"] = 1
        return stats


async def _check_notification_exists(session, user_id: int, notif_type_value: str, data_match: dict) -> bool:
    """Проверка существования уведомления с заданными параметрами."""
    from sqlalchemy import func, cast, String
    query = select(func.count(Notification.id)).where(
        and_(
            Notification.user_id == user_id,
            cast(Notification.type, String) == notif_type_value,
            *[cast(Notification.data[key], String) == str(value) for key, value in data_match.items()]
        )
    )
    result = await session.execute(query)
    count = result.scalar_one()
    return count > 0


async def _create_object_notification(
    session, 
    obj: Object, 
    owner: User, 
    notif_type: NotificationType, 
    template_vars: dict,
    scheduled_at: datetime
):
    """Создание уведомлений для объекта (TG + In-App)."""
    # Проверить настройки владельца
    prefs = owner.notification_preferences or {}
    type_code = notif_type.value
    type_prefs = prefs.get(type_code, {})
    
    telegram_enabled = type_prefs.get("telegram", True)
    inapp_enabled = type_prefs.get("inapp", True)
    
    from shared.templates.notifications.base_templates import NotificationTemplateManager
    
    # Создать TG уведомление
    if telegram_enabled:
        rendered_tg = NotificationTemplateManager.render(notif_type, NotificationChannel.TELEGRAM, template_vars)
        notification_tg = Notification(
            user_id=owner.id,
            type=notif_type.value,  # Используем .value для совместимости с БД
            channel=NotificationChannel.TELEGRAM.value,
            priority=NotificationPriority.HIGH if "late" in type_code or "early" in type_code or "no_shifts" in type_code else NotificationPriority.NORMAL,
            title=rendered_tg["title"],
            message=rendered_tg["message"],
            data={**template_vars, "object_id": current_obj.id},
            scheduled_at=scheduled_at
        )
        session.add(notification_tg)
    
    # Создать In-App уведомление
    if inapp_enabled:
        rendered_inapp = NotificationTemplateManager.render(notif_type, NotificationChannel.IN_APP, template_vars)
        notification_inapp = Notification(
            user_id=owner.id,
            type=notif_type.value,  # Используем .value для совместимости с БД
            channel=NotificationChannel.IN_APP.value,
            priority=NotificationPriority.HIGH if "late" in type_code or "early" in type_code or "no_shifts" in type_code else NotificationPriority.NORMAL,
            title=rendered_inapp["title"],
            message=rendered_inapp["message"],
            data={**template_vars, "object_id": current_obj.id},
            scheduled_at=scheduled_at
        )
        session.add(notification_inapp)
    
    await session.commit()
    
    logger.info(
        f"Created {notif_type.value} notification for owner {owner.id}",
        object_id=current_obj.id,
        telegram=telegram_enabled,
        inapp=inapp_enabled
    )

