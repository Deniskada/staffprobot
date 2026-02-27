"""Celery задачи: поздравления с Днём Рождения и государственными праздниками."""

from celery import Task
from core.celery.celery_app import celery_app
from core.logging.logger import logger

# Государственные праздники РФ: (день, месяц, название, эмодзи)
RF_HOLIDAYS = [
    (1,  1,  "Новый год",                          "🎆"),
    (7,  1,  "Рождество Христово",                 "🎄"),
    (23, 2,  "День защитника Отечества",           "🎖️"),
    (8,  3,  "Международный женский день",         "🌸"),
    (1,  5,  "Праздник Весны и Труда",             "🌷"),
    (9,  5,  "День Победы",                        "🎗️"),
    (12, 6,  "День России",                        "🇷🇺"),
    (4,  11, "День народного единства",            "🤝"),
]


class BirthdayTask(Task):
    """Базовый класс задачи поздравлений."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"birthday_task failed: {exc}")


@celery_app.task(base=BirthdayTask, bind=True, name="send_birthday_greetings")
def send_birthday_greetings(self):
    """Поздравить сотрудников с ДР: генерация текста Yandex GPT + рассылка."""
    import asyncio
    try:
        return asyncio.run(_send_birthday_greetings_async())
    except Exception as e:
        logger.error(f"send_birthday_greetings failed: {e}")
        raise


async def _send_birthday_greetings_async():
    from datetime import datetime, date
    from sqlalchemy import select, and_, extract, func as sqlfunc
    from sqlalchemy.orm import selectinload
    import pytz

    from core.database.session import get_celery_session
    from core.config.settings import settings
    from domain.entities.user import User
    from domain.entities.contract import Contract
    from domain.entities.object import Object
    from shared.services.yandex_gpt_service import generate_birthday_greeting
    from telegram import Bot

    moscow_tz = pytz.timezone("Europe/Moscow")
    today_msk = datetime.now(moscow_tz).date()
    today_day = today_msk.day
    today_month = today_msk.month

    bot = Bot(token=settings.telegram_bot_token)
    sent_count = 0
    errors = []

    async with get_celery_session() as session:
        # Найти активных сотрудников с ДР сегодня (сравниваем день и месяц)
        employees_q = await session.execute(
            select(User).where(
                and_(
                    User.birth_date.isnot(None),
                    extract("day", User.birth_date) == today_day,
                    extract("month", User.birth_date) == today_month,
                    User.is_active == True,
                )
            )
        )
        employees = employees_q.scalars().all()

        if not employees:
            logger.info("send_birthday_greetings: нет именинников сегодня")
            return {"sent": 0, "errors": []}

        logger.info(f"send_birthday_greetings: именинников сегодня — {len(employees)}")

        for employee in employees:
            try:
                # Найти активные договоры сотрудника
                contracts_q = await session.execute(
                    select(Contract).where(
                        and_(
                            Contract.employee_id == employee.id,
                            Contract.status == "active",
                        )
                    )
                )
                contracts = contracts_q.scalars().all()

                if not contracts:
                    continue

                # Генерировать поздравление
                greeting = await generate_birthday_greeting(
                    employee.first_name, employee.last_name
                )
                if not greeting:
                    greeting = f"🎂 Поздравляем {employee.first_name} с Днём Рождения!"

                message = f"🎉 *День Рождения!*\n\n{greeting}"

                # Уникальные владельцы и объекты по всем договорам
                owner_ids = {c.owner_id for c in contracts}
                object_ids: set[int] = set()
                for c in contracts:
                    if c.allowed_objects:
                        object_ids.update(c.allowed_objects)

                sent_to: set = set()

                # 1. Поздравить самого сотрудника
                if employee.telegram_id and employee.telegram_id not in sent_to:
                    try:
                        await bot.send_message(
                            chat_id=employee.telegram_id,
                            text=message,
                            parse_mode="Markdown",
                        )
                        sent_to.add(employee.telegram_id)
                        sent_count += 1
                    except Exception as e:
                        errors.append(f"employee {employee.id}: {e}")

                # 2. Поздравить владельцев (если включено в настройках)
                for owner_id in owner_ids:
                    owner_q = await session.execute(
                        select(User).where(User.id == owner_id)
                    )
                    owner = owner_q.scalar_one_or_none()
                    if not owner:
                        continue

                    prefs = owner.notification_preferences or {}
                    birthday_pref = prefs.get("employee_birthday", {})
                    if birthday_pref.get("telegram", True) is False:
                        continue

                    if owner.telegram_id and owner.telegram_id not in sent_to:
                        try:
                            await bot.send_message(
                                chat_id=owner.telegram_id,
                                text=message,
                                parse_mode="Markdown",
                            )
                            sent_to.add(owner.telegram_id)
                            sent_count += 1
                        except Exception as e:
                            errors.append(f"owner {owner_id}: {e}")

                    # 3. Найти менеджеров владельца и поздравить их
                    managers_q = await session.execute(
                        select(User)
                        .join(Contract, Contract.employee_id == User.id)
                        .where(
                            and_(
                                Contract.owner_id == owner_id,
                                Contract.status == "active",
                                User.role == "manager",
                            )
                        )
                    )
                    managers = managers_q.scalars().all()
                    for manager in managers:
                        if manager.telegram_id and manager.telegram_id not in sent_to:
                            try:
                                await bot.send_message(
                                    chat_id=manager.telegram_id,
                                    text=message,
                                    parse_mode="Markdown",
                                )
                                sent_to.add(manager.telegram_id)
                                sent_count += 1
                            except Exception as e:
                                errors.append(f"manager {manager.id}: {e}")

                # 4. Отправить в TG-группы объектов
                if object_ids:
                    objs_q = await session.execute(
                        select(Object).where(Object.id.in_(list(object_ids)))
                    )
                    objects = objs_q.scalars().all()
                    for obj in objects:
                        chat_id = getattr(obj, "telegram_report_chat_id", None)
                        if chat_id and chat_id not in sent_to:
                            try:
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=message,
                                    parse_mode="Markdown",
                                )
                                sent_to.add(chat_id)
                                sent_count += 1
                            except Exception as e:
                                errors.append(f"object {obj.id} group: {e}")

                logger.info(
                    f"send_birthday_greetings: поздравлен {employee.first_name} "
                    f"{employee.last_name or ''} (id={employee.id}), "
                    f"отправлено {len(sent_to)} сообщений"
                )

            except Exception as e:
                error_msg = f"Ошибка для сотрудника {employee.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

    logger.info(f"send_birthday_greetings: всего отправлено {sent_count}, ошибок {len(errors)}")
    return {"sent": sent_count, "errors": errors}


@celery_app.task(base=BirthdayTask, bind=True, name="send_holiday_greetings")
def send_holiday_greetings(self):
    """Поздравить коллективы объектов с государственными праздниками РФ."""
    import asyncio
    try:
        return asyncio.run(_send_holiday_greetings_async())
    except Exception as e:
        logger.error(f"send_holiday_greetings failed: {e}")
        raise


async def _send_holiday_greetings_async():
    from datetime import datetime
    from sqlalchemy import select, and_
    import pytz

    from core.database.session import get_celery_session
    from core.config.settings import settings
    from domain.entities.user import User
    from domain.entities.object import Object
    from shared.services.yandex_gpt_service import generate_holiday_greeting
    from telegram import Bot

    moscow_tz = pytz.timezone("Europe/Moscow")
    today = datetime.now(moscow_tz).date()

    # Проверяем, есть ли сегодня праздник
    holiday = next(
        ((d, m, name, emoji) for d, m, name, emoji in RF_HOLIDAYS
         if d == today.day and m == today.month),
        None,
    )

    if not holiday:
        logger.info("send_holiday_greetings: сегодня нет праздников")
        return {"sent": 0, "holiday": None}

    _, _, holiday_name, holiday_emoji = holiday
    logger.info(f"send_holiday_greetings: сегодня — {holiday_name}")

    # Генерируем поздравление
    greeting = await generate_holiday_greeting(holiday_name)
    if not greeting:
        greeting = f"Поздравляем весь коллектив с праздником — {holiday_name}!"

    message = f"{holiday_emoji} *{holiday_name}!*\n\n{greeting}"

    bot = Bot(token=settings.telegram_bot_token)
    sent_count = 0
    errors = []

    async with get_celery_session() as session:
        # Получаем всех активных владельцев
        owners_q = await session.execute(
            select(User).where(
                and_(User.is_active == True, User.role == "owner")
            )
        )
        owners = owners_q.scalars().all()

        for owner in owners:
            # Проверяем настройку уведомления
            prefs = owner.notification_preferences or {}
            holiday_pref = prefs.get("employee_holiday_greeting", {})
            if holiday_pref.get("telegram", True) is False:
                continue

            # Получаем объекты владельца с telegram-группой
            objects_q = await session.execute(
                select(Object).where(
                    and_(
                        Object.owner_id == owner.id,
                        Object.is_active == True,
                        Object.telegram_report_chat_id.isnot(None),
                    )
                )
            )
            objects = objects_q.scalars().all()

            sent_to: set = set()

            for obj in objects:
                chat_id = obj.telegram_report_chat_id
                if not chat_id or chat_id in sent_to:
                    continue
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown",
                    )
                    sent_to.add(chat_id)
                    sent_count += 1
                    logger.info(f"Праздник: отправлено в группу {chat_id} (объект {obj.id})")
                except Exception as e:
                    errors.append(f"object {obj.id} group {chat_id}: {e}")
                    logger.warning(f"Ошибка отправки в группу {chat_id}: {e}")

    logger.info(
        f"send_holiday_greetings: {holiday_name} — отправлено {sent_count} групп, ошибок {len(errors)}"
    )
    return {"sent": sent_count, "holiday": holiday_name, "errors": errors}
