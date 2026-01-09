"""Celery задачи для создания напоминаний о сменах и объектах."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from celery import Task
from sqlalchemy import select, and_, or_, exists
from sqlalchemy.orm import selectinload

from core.celery.celery_app import celery_app
from core.logging.logger import logger
from core.database.session import get_async_session
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.user import User
from domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from shared.services.shift_notification_service import ShiftNotificationService


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
            # Время проверки: через 1 час (окно 50-75 минут для учета погрешности)
            # Задача запускается каждые 5 минут, поэтому окно должно быть шире, чтобы не пропустить смены
            now = datetime.now(timezone.utc)
            target_time_start = now + timedelta(minutes=50)
            target_time_end = now + timedelta(minutes=75)
            
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
                target_range=f"{target_time_start} - {target_time_end}",
                now_utc=now.isoformat(),
                target_start=target_time_start.isoformat(),
                target_end=target_time_end.isoformat()
            )
            
            # Дополнительная диагностика: проверим все смены в ближайшие 2 часа
            if len(upcoming_shifts) == 0:
                debug_query = select(ShiftSchedule).options(
                    selectinload(ShiftSchedule.user),
                    selectinload(ShiftSchedule.object)
                ).where(
                    and_(
                        ShiftSchedule.planned_start >= now,
                        ShiftSchedule.planned_start <= now + timedelta(hours=2),
                        ShiftSchedule.status.in_(["planned", "confirmed"])
                    )
                ).order_by(ShiftSchedule.planned_start)
                debug_result = await session.execute(debug_query)
                debug_shifts = debug_result.scalars().all()
                logger.debug(
                    f"Debug: Found {len(debug_shifts)} shifts in next 2 hours",
                    shifts_info=[{
                        "id": s.id,
                        "planned_start": s.planned_start.isoformat() if s.planned_start else None,
                        "status": s.status,
                        "user_id": s.user_id
                    } for s in debug_shifts[:5]]  # Первые 5 для примера
                )
            
            notification_service = ShiftNotificationService()
            for shift_schedule in upcoming_shifts:
                try:
                    sent = await notification_service.notify_shift_reminder(shift_schedule.id)
                    if sent:
                        created_count += 1
                    else:
                        skipped_count += 1
                    
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


@celery_app.task(base=ReminderTask, bind=True, name="check_shifts_did_not_start")
def check_shifts_did_not_start(self) -> Dict[str, Any]:
    """
    Проверка несостоявшихся смен.
    Запускается каждые 10 минут.
    
    Создает уведомления SHIFT_DID_NOT_START для запланированных смен,
    которые не начались через час после планового начала.
    
    Returns:
        Статистика: сколько уведомлений создано
    """
    try:
        import asyncio
        return asyncio.run(_check_shifts_did_not_start_async())
    except Exception as e:
        logger.error(f"check_shifts_did_not_start failed: {e}")
        raise


async def _check_shifts_did_not_start_async() -> Dict[str, Any]:
    """Асинхронная логика проверки несостоявшихся смен."""
    stats = {
        "checked": 0,
        "notifications_created": 0,
        "skipped": 0,
        "errors": 0
    }
    
    try:
        async with get_async_session() as session:
            now = datetime.now(timezone.utc)
            # Проверяем смены, которые должны были начаться более часа назад
            # но не более 24 часов назад (чтобы не проверять старые смены)
            one_hour_ago = now - timedelta(hours=1)
            one_day_ago = now - timedelta(hours=24)
            
            # Находим запланированные смены, которые не начались
            query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.user),
                selectinload(ShiftSchedule.object).selectinload(Object.owner)
            ).where(
                and_(
                    ShiftSchedule.planned_start >= one_day_ago,
                    ShiftSchedule.planned_start <= one_hour_ago,
                    ShiftSchedule.status.in_(["planned", "confirmed"]),
                    # Проверяем, что нет реальной смены, которая началась
                    ~exists(
                        select(Shift.id).where(
                            and_(
                                Shift.schedule_id == ShiftSchedule.id,
                                Shift.status.in_(["active", "completed"]),
                                Shift.start_time.isnot(None)
                            )
                        )
                    )
                )
            )
            
            result = await session.execute(query)
            schedules = result.scalars().all()
            
            logger.info(
                f"Found {len(schedules)} shifts that did not start",
                one_hour_ago=one_hour_ago.isoformat(),
                now=now.isoformat()
            )
            
            from shared.services.shift_notification_service import ShiftNotificationService
            notification_service = ShiftNotificationService()
            
            for schedule in schedules:
                try:
                    stats["checked"] += 1
                    
                    if not schedule.object or not schedule.object.owner:
                        stats["skipped"] += 1
                        continue
                    
                    # Проверяем, не создано ли уже уведомление для этой смены
                    from shared.services.notification_service import NotificationService
                    notif_service = NotificationService()
                    
                    # Проверяем существование уведомления
                    notification_exists = await _check_notification_exists(
                        session,
                        schedule.object.owner_id,
                        NotificationType.SHIFT_DID_NOT_START.value,
                        {"shift_schedule_id": schedule.id}
                    )
                    
                    if notification_exists:
                        stats["skipped"] += 1
                        continue
                    
                    # Создаем уведомление
                    await notification_service.notify_shift_did_not_start(schedule.id)
                    stats["notifications_created"] += 1
                    
                except Exception as e:
                    logger.error(
                        f"Error processing shift_schedule {schedule.id}: {e}",
                        schedule_id=schedule.id,
                        error=str(e)
                    )
                    stats["errors"] += 1
                    continue
            
            logger.info(
                f"Shifts did not start check completed: checked={stats['checked']}, "
                f"created={stats['notifications_created']}, skipped={stats['skipped']}, errors={stats['errors']}"
            )
            return stats
            
    except Exception as e:
        import traceback
        logger.error(f"Fatal error in _check_shifts_did_not_start_async: {e}\n{traceback.format_exc()}")
        stats["errors"] = 1
        return stats


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
        
        # Получить ID всех активных объектов
        async with get_async_session() as session:
            query = select(Object.id).where(Object.is_active == True)
            result = await session.execute(query)
            object_ids = [row[0] for row in result.all()]
        
        # Обрабатываем каждый объект в отдельной транзакции
        for obj_id in object_ids:
            current_obj_id = obj_id  # Сохраняем для обработки ошибок
            try:
                async with get_async_session() as session:
                    # Загружаем объект заново с owner в текущей сессии
                    obj_query = select(Object).options(
                        selectinload(Object.owner)
                    ).where(Object.id == obj_id)
                    obj_result = await session.execute(obj_query)
                    current_obj = obj_result.scalar_one_or_none()
                    
                    if not current_obj or not current_obj.owner:
                        continue
                    
                    # Получить смены объекта на сегодня (учитываем как запланированные, так и спонтанные)
                    start_of_day_utc = timezone_helper.start_of_day_utc(today_local)
                    end_of_day_utc = timezone_helper.end_of_day_utc(today_local)
                    shifts_query = select(Shift).where(
                        and_(
                            Shift.object_id == current_obj.id,
                            or_(
                                # Запланированные смены
                                and_(
                                    Shift.planned_start.isnot(None),
                                    Shift.planned_start >= start_of_day_utc,
                                    Shift.planned_start < end_of_day_utc
                                ),
                                # Спонтанные смены (без planned_start, но с start_time или actual_start)
                                and_(
                                    Shift.planned_start.is_(None),
                                    or_(
                                        and_(
                                            Shift.start_time.isnot(None),
                                            Shift.start_time >= start_of_day_utc,
                                            Shift.start_time < end_of_day_utc
                                        ),
                                        and_(
                                            Shift.actual_start.isnot(None),
                                            Shift.actual_start >= start_of_day_utc,
                                            Shift.actual_start < end_of_day_utc
                                        )
                                    )
                                )
                            )
                        )
                    ).options(selectinload(Shift.user))
                    
                    shifts_result = await session.execute(shifts_query)
                    shifts_today = list(shifts_result.scalars().all())
                    
                    logger.info(f"Object {current_obj.id} ({current_obj.name}): {len(shifts_today)} shifts found, opening_time={current_obj.opening_time}, closing_time={current_obj.closing_time}")
                    
                    # Проверка 1: НЕТ СМЕН НА ОБЪЕКТЕ
                    # Уведомление "нет активных смен" должно приходить каждый раз, когда задача отрабатывает
                    if not shifts_today and current_obj.opening_time:
                        # Проверяем после времени открытия
                        expected_open_time = datetime.combine(today_local, current_obj.opening_time).replace(tzinfo=timezone_helper.local_tz)
                        if now >= expected_open_time.astimezone(timezone.utc):
                            # НЕ проверяем существование - уведомление должно приходить каждый раз
                            await _create_object_notification(
                                session, current_obj.id, current_obj.owner, NotificationType.OBJECT_NO_SHIFTS_TODAY,
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
                        # Найти первую и последнюю смену (учитываем actual_start, start_time, planned_start)
                        first_shift = min(shifts_today, key=lambda s: s.actual_start or s.start_time or s.planned_start or datetime.max.replace(tzinfo=timezone.utc))
                        last_shift = max(shifts_today, key=lambda s: s.end_time or s.start_time or datetime.min.replace(tzinfo=timezone.utc))
                        logger.info(f"Object {current_obj.id}: first_shift={first_shift.id}, last_shift={last_shift.id}, last_status={last_shift.status}, last_end_time={last_shift.end_time}")
                        
                        # Проверка 2: ОТКРЫТИЕ ОБЪЕКТА (вовремя или с опозданием)
                        if first_shift.actual_start:
                            expected_open = datetime.combine(today_local, current_obj.opening_time).replace(tzinfo=timezone_helper.local_tz)
                            actual_open_local = timezone_helper.utc_to_local(first_shift.actual_start)
                            
                            delay_minutes = int((actual_open_local - expected_open).total_seconds() / 60)
                            
                            # Уже создавали уведомление для этого объекта на сегодня?
                            # Проверяем по дате, чтобы не создавать дубликаты при каждом запуске задачи
                            notif_type = NotificationType.OBJECT_LATE_OPENING if delay_minutes > 5 else NotificationType.OBJECT_OPENED
                            notification_exists = await _check_notification_exists(
                                session, current_obj.owner_id, 
                                notif_type.value,  # Передаём строковое значение
                                {"object_id": current_obj.id, "date": str(today_local)}
                            )
                            
                            if not notification_exists:
                                if delay_minutes > 5:  # Опоздание больше 5 минут
                                    await _create_object_notification(
                                        session, current_obj.id, current_obj.owner, NotificationType.OBJECT_LATE_OPENING,
                                        {
                                            "object_id": current_obj.id,
                                            "date": str(today_local),
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
                                        session, current_obj.id, current_obj.owner, NotificationType.OBJECT_OPENED,
                                        {
                                            "object_id": current_obj.id,
                                            "date": str(today_local),
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
                            
                            # Уже создавали уведомление для этого объекта на сегодня?
                            # Проверяем по дате, чтобы не создавать дубликаты при каждом запуске задачи
                            notif_type_close = NotificationType.OBJECT_EARLY_CLOSING if early_minutes > 5 else NotificationType.OBJECT_CLOSED
                            notification_exists = await _check_notification_exists(
                                session, current_obj.owner_id,
                                notif_type_close.value,  # Передаём строковое значение
                                {"object_id": current_obj.id, "date": str(today_local)}
                            )
                            
                            if not notification_exists:
                                if early_minutes > 5:  # Раннее закрытие больше 5 минут
                                    await _create_object_notification(
                                        session, current_obj.id, current_obj.owner, NotificationType.OBJECT_EARLY_CLOSING,
                                        {
                                            "object_id": current_obj.id,
                                            "date": str(today_local),
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
                                        session, current_obj.id, current_obj.owner, NotificationType.OBJECT_CLOSED,
                                        {
                                            "object_id": current_obj.id,
                                            "date": str(today_local),
                                            "object_name": current_obj.name,
                                            "employee_name": f"{last_shift.user.first_name} {last_shift.user.last_name}" if last_shift.user else "Неизвестный",
                                            "close_time": actual_close_local.strftime("%H:%M")
                                        },
                                        now
                                    )
                                    stats["closed"] += 1
                            
                            # Проверка 4: После закрытия всех смен - объект без смен до конца дня
                            # Если все смены завершены и объект закрылся, создаем уведомление "нет смен"
                            all_shifts_completed = all(s.status in ('completed', 'closed') for s in shifts_today)
                            
                            if all_shifts_completed and last_shift.end_time:
                                # Создаем уведомление через 10 минут после закрытия последней смены
                                # НЕ проверяем существование - уведомление должно приходить каждый раз, когда задача отрабатывает
                                close_time_utc = last_shift.end_time
                                delay_minutes = 10
                                notification_time = close_time_utc + timedelta(minutes=delay_minutes)
                                
                                if now >= notification_time:
                                    await _create_object_notification(
                                        session, current_obj.id, current_obj.owner, NotificationType.OBJECT_NO_SHIFTS_TODAY,
                                        {
                                            "object_name": current_obj.name,
                                            "object_address": current_obj.address or "",
                                            "date": today_local.strftime("%d.%m.%Y")
                                        },
                                        now
                                    )
                                    stats["no_shifts"] += 1
                    
            except Exception as e:
                error_obj_id = current_obj_id if 'current_obj_id' in locals() else 'unknown'
                logger.error(f"Error checking object {error_obj_id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                stats["errors"] += 1
                continue
        
        logger.info(f"Object openings check completed: opened={stats['opened']}, late_opening={stats['late_opening']}, no_shifts={stats['no_shifts']}, early_closing={stats['early_closing']}, closed={stats['closed']}, errors={stats['errors']}")
        return stats
            
    except Exception as e:
        import traceback
        logger.error(f"Fatal error in _check_object_openings_async: {e}\n{traceback.format_exc()}")
        stats["errors"] = 1
        return stats


async def _check_notification_exists(session, user_id: int, notif_type_value: str, data_match: dict) -> bool:
    """Проверка существования уведомления с заданными параметрами."""
    from sqlalchemy import func, cast, String, text
    # Для JSONB полей используем правильный синтаксис PostgreSQL через raw SQL
    conditions = [
        Notification.user_id == user_id,
        cast(Notification.type, String) == notif_type_value
    ]
    
    # Добавляем условия для каждого ключа в data_match через JSONB оператор ->>
    for key, value in data_match.items():
        # Используем JSONB оператор ->> для доступа к полю как тексту
        conditions.append(
            text(f"notifications.data->>'{key}' = :{key}")
        )
    
    # Формируем параметры для подстановки
    params = {key: str(value) for key, value in data_match.items()}
    
    query = select(func.count(Notification.id)).where(and_(*conditions))
    result = await session.execute(query, params)
    count = result.scalar_one()
    
    logger.debug(
        f"_check_notification_exists: user_id={user_id}, type={notif_type_value}, "
        f"data_match={data_match}, found_count={count}"
    )
    
    return count > 0


async def _create_object_notification(
    session, 
    obj_id: int,
    owner: User,
    notif_type: NotificationType,
    template_vars: dict,
    scheduled_at: datetime
):
    """Создание уведомлений для объекта (TG + In-App)."""
    # Загрузить owner заново из БД, чтобы получить актуальные настройки
    # JSONB поля могут не обновляться через refresh, поэтому загружаем заново
    owner_query = select(User).where(User.id == owner.id)
    owner_result = await session.execute(owner_query)
    current_owner = owner_result.scalar_one_or_none()
    
    if not current_owner:
        logger.error(f"Owner {owner.id} not found when creating notification")
        return
    
    # Проверить настройки владельца
    prefs = current_owner.notification_preferences or {}
    type_code = notif_type.value
    type_prefs = prefs.get(type_code, {})
    
    # Если настройка найдена в словаре, используем её значение
    # Если настройка не найдена (type_code отсутствует в prefs), используем значение по умолчанию True
    telegram_enabled = type_prefs.get("telegram", True) if type_code in prefs else True
    inapp_enabled = type_prefs.get("inapp", True) if type_code in prefs else True
    
    logger.info(
        f"Notification settings for owner {current_owner.id}, type {type_code}: "
        f"telegram={telegram_enabled}, inapp={inapp_enabled}, "
        f"prefs_keys={list(prefs.keys())}, type_prefs={type_prefs}"
    )
    
    from shared.templates.notifications.base_templates import NotificationTemplateManager
    
    # Используем SQL INSERT с приведением типа для enum в БД
    from sqlalchemy import text
    import json
    
    # В БД хранятся имена enum (HIGH, NORMAL), а не значения
    priority_enum = NotificationPriority.HIGH if "late" in type_code or "early" in type_code or "no_shifts" in type_code else NotificationPriority.NORMAL
    priority_str = priority_enum.name  # HIGH или NORMAL
    type_name = notif_type.value  # Используем значение enum (строку)
    
    # Создать TG уведомление
    if telegram_enabled:
        rendered_tg = NotificationTemplateManager.render(notif_type, NotificationChannel.TELEGRAM, template_vars)
        data_json = json.dumps({**template_vars, "object_id": obj_id})
        await session.execute(
            text("""
                INSERT INTO notifications (user_id, type, channel, status, priority, title, message, data, scheduled_at)
                VALUES (:user_id, CAST(:type AS notificationtype), CAST(:channel AS notificationchannel), 
                        CAST(:status AS notificationstatus), CAST(:priority AS notificationpriority),
                        :title, :message, CAST(:data AS jsonb), :scheduled_at)
            """),
            {
                "user_id": current_owner.id,
                "type": type_name,
                "channel": NotificationChannel.TELEGRAM.name,  # В БД хранится имя enum (TELEGRAM), а не значение
                "status": NotificationStatus.PENDING.name,  # В БД хранится имя enum (PENDING)
                "priority": priority_str,
                "title": rendered_tg["title"],
                "message": rendered_tg["message"],
                "data": data_json,
                "scheduled_at": scheduled_at
            }
        )
    
    # Создать In-App уведомление
    if inapp_enabled:
        rendered_inapp = NotificationTemplateManager.render(notif_type, NotificationChannel.IN_APP, template_vars)
        # Включаем object_id и date в data для проверки дубликатов
        data_json = json.dumps({**template_vars})
        await session.execute(
            text("""
                INSERT INTO notifications (user_id, type, channel, status, priority, title, message, data, scheduled_at)
                VALUES (:user_id, CAST(:type AS notificationtype), CAST(:channel AS notificationchannel), 
                        CAST(:status AS notificationstatus), CAST(:priority AS notificationpriority),
                        :title, :message, CAST(:data AS jsonb), :scheduled_at)
            """),
            {
                "user_id": current_owner.id,
                "type": type_name,
                "channel": NotificationChannel.IN_APP.name,  # В БД хранится имя enum (IN_APP), а не значение
                "status": NotificationStatus.PENDING.name,  # В БД хранится имя enum (PENDING)
                "priority": priority_str,
                "title": rendered_inapp["title"],
                "message": rendered_inapp["message"],
                "data": data_json,
                "scheduled_at": scheduled_at
            }
        )
    
    await session.commit()
    
    logger.info(
        f"Created {notif_type.value} notification for owner {current_owner.id}",
        object_id=obj_id,
        telegram=telegram_enabled,
        inapp=inapp_enabled
    )

