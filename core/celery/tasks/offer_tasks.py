"""Celery задачи: напоминания о неподписанных офертах."""

import asyncio
from celery import Task
from core.celery.celery_app import celery_app
from core.logging.logger import logger


class OfferTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"offer_task failed: {exc}")


@celery_app.task(base=OfferTask, bind=True, name="send_offer_reminders")
def send_offer_reminders(self):
    """Напомнить сотрудникам о неподписанных офертах (>24ч)."""
    try:
        return asyncio.run(_send_offer_reminders_async())
    except Exception as e:
        logger.error(f"send_offer_reminders failed: {e}")
        raise


async def _send_offer_reminders_async():
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, and_
    from core.database.session import get_celery_session
    from domain.entities.contract import Contract
    from domain.entities.user import User

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=24)

    sent = 0
    async with get_celery_session() as session:
        stmt = select(Contract).where(
            and_(
                Contract.status == "pending_acceptance",
                Contract.is_active.is_(True),
                Contract.created_at < threshold,
            )
        )
        result = await session.execute(stmt)
        contracts = result.scalars().all()

        if not contracts:
            logger.info("offer_reminders: no pending offers older than 24h")
            return {"sent": 0}

        for contract in contracts:
            try:
                employee = await session.get(User, contract.employee_id)
                if not employee or not employee.telegram_id:
                    continue

                from telegram import Bot
                from core.config.settings import settings
                bot = Bot(token=settings.telegram_bot_token)

                text = (
                    f"📋 Напоминание: у вас есть неподписанная оферта\n\n"
                    f"«{contract.title}» (№ {contract.contract_number})\n"
                    f"Создана: {contract.created_at.strftime('%d.%m.%Y')}\n\n"
                    f"Перейдите в раздел «Договоры» для подписания."
                )

                await bot.send_message(chat_id=employee.telegram_id, text=text)
                sent += 1
            except Exception as e:
                logger.error(f"offer_reminder send failed for contract {contract.id}: {e}")

    logger.info(f"offer_reminders: sent {sent} reminders")
    return {"sent": sent}
