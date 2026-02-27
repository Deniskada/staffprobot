"""Celery задача: поздравления сотрудников с Днём Рождения."""

from celery import Task
from core.celery.celery_app import celery_app
from core.logging.logger import logger


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
