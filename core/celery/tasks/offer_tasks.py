"""Celery задачи: напоминания о неподписанных офертах, автоэкспирация."""

import asyncio
from celery import Task
from core.celery.celery_app import celery_app
from core.logging.logger import logger


class OfferTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"offer_task failed: {exc}")


@celery_app.task(base=OfferTask, bind=True, name="send_offer_reminders")
def send_offer_reminders(self):
    """Напомнить сотрудникам о неподписанных офертах (>24ч), эскалировать owner (>3д), автоэкспирация."""
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
    from domain.entities.contract_history import ContractHistory, ContractChangeType
    from domain.entities.user import User

    now = datetime.now(timezone.utc)
    threshold_24h = now - timedelta(hours=24)
    threshold_3d = now - timedelta(days=3)

    sent_employee = 0
    sent_owner = 0
    expired_count = 0

    async with get_celery_session() as session:
        stmt = select(Contract).where(
            and_(
                Contract.status == "pending_acceptance",
                Contract.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        contracts = result.scalars().all()

        if not contracts:
            logger.info("offer_reminders: no pending offers")
            return {"sent_employee": 0, "sent_owner": 0, "expired": 0}

        from telegram import Bot
        from core.config.settings import settings
        bot = Bot(token=settings.telegram_bot_token)

        for contract in contracts:
            try:
                # 1. Автоэкспирация по expires_at
                if contract.expires_at and contract.expires_at <= now:
                    contract.status = "expired"
                    contract.is_active = False
                    from shared.services.contract_history_service import log_contract_event
                    await log_contract_event(
                        session, contract.id, ContractChangeType.EXPIRED,
                        details={"expires_at": contract.expires_at.isoformat()},
                    )
                    expired_count += 1
                    logger.info(f"Contract {contract.id} expired (expires_at={contract.expires_at})")
                    continue

                # Пропускаем свежие (<24ч)
                if contract.created_at >= threshold_24h:
                    continue

                # 2. Дедупликация: не отправлять, если напоминание было <24ч назад
                last_reminder = await session.execute(
                    select(ContractHistory.changed_at)
                    .where(
                        ContractHistory.contract_id == contract.id,
                        ContractHistory.change_type == ContractChangeType.REMINDER_SENT.value,
                    )
                    .order_by(ContractHistory.changed_at.desc())
                    .limit(1)
                )
                last_ts = last_reminder.scalar_one_or_none()
                if last_ts and last_ts >= threshold_24h:
                    continue

                employee = await session.get(User, contract.employee_id)
                if not employee or not employee.telegram_id:
                    continue

                # 3. Срочное напоминание за день до expires_at
                urgent = ""
                if contract.expires_at:
                    remaining = contract.expires_at - now
                    if remaining <= timedelta(days=1):
                        urgent = "\n⚠️ Срок подписания истекает менее чем через 24 часа!"

                from core.auth.auto_login import build_auto_login_url
                from core.utils.url_helper import URLHelper
                base_url = await URLHelper.get_web_url()
                offer_url = await build_auto_login_url(
                    employee.id, f"/employee/offers/{contract.id}", base_url
                )

                text = (
                    f"📋 Напоминание: у вас есть неподписанный договор\n\n"
                    f"«{contract.title}» (№ {contract.contract_number})\n"
                    f"Создан: {contract.created_at.strftime('%d.%m.%Y')}"
                    f"{urgent}\n\n"
                    f"🔗 Подписать: {offer_url}"
                )

                await bot.send_message(chat_id=employee.telegram_id, text=text)
                sent_employee += 1

                # Логируем напоминание
                from shared.services.contract_history_service import log_contract_event
                await log_contract_event(
                    session, contract.id, ContractChangeType.REMINDER_SENT,
                    details={"target": "employee"},
                )

                # 4. Эскалация: если >3 дней — уведомить owner
                if contract.created_at < threshold_3d:
                    owner = await session.get(User, contract.owner_id)
                    if owner and owner.telegram_id:
                        emp_name = employee.first_name or f"ID {employee.id}"
                        owner_url = await build_auto_login_url(
                            owner.id,
                            f"/owner/employees/contract/{contract.id}",
                            base_url,
                        )
                        owner_text = (
                            f"⏰ Сотрудник {emp_name} не подписал договор\n\n"
                            f"«{contract.title}» (№ {contract.contract_number})\n"
                            f"Создан: {contract.created_at.strftime('%d.%m.%Y')}\n"
                            f"Прошло более 3 дней.\n\n"
                            f"🔗 {owner_url}"
                        )
                        await bot.send_message(chat_id=owner.telegram_id, text=owner_text)
                        sent_owner += 1
                        await log_contract_event(
                            session, contract.id, ContractChangeType.REMINDER_SENT,
                            details={"target": "owner", "reason": "escalation_3d"},
                        )

            except Exception as e:
                logger.error(f"offer_reminder failed for contract {contract.id}: {e}")

        await session.commit()

    logger.info(f"offer_reminders: sent_employee={sent_employee}, sent_owner={sent_owner}, expired={expired_count}")
    return {"sent_employee": sent_employee, "sent_owner": sent_owner, "expired": expired_count}
