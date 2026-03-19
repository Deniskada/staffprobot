"""Сервис привязок мессенджеров и OAuth к пользователям."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.messenger_account import MessengerAccount
from domain.entities.user import User


async def get_user_id_from_provider(
    session: AsyncSession,
    provider: str,
    external_user_id: str,
) -> Optional[int]:
    """
    Резолвинг user_id по провайдеру и внешнему идентификатору.

    provider: telegram | max | yandex_id | tinkoff_id
    external_user_id: ID в системе провайдера (str для универсальности).

    Returns:
        Внутренний user_id или None.
    """
    stmt = select(MessengerAccount.user_id).where(
        MessengerAccount.provider == provider,
        MessengerAccount.external_user_id == str(external_user_id),
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row[0] if row else None


async def get_telegram_chat_id_for_user(
    session: AsyncSession,
    user_id: int,
) -> Optional[str]:
    """
    Получить chat_id для отправки в Telegram по user_id.

    Сначала messenger_accounts (provider=telegram), fallback — user.telegram_id.
    """
    stmt = select(MessengerAccount.chat_id).where(
        MessengerAccount.user_id == user_id,
        MessengerAccount.provider == "telegram",
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row and row[0]:
        return str(row[0])
    # Fallback: users.telegram_id (legacy)
    user_stmt = select(User.telegram_id).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    tg_row = user_result.scalar_one_or_none()
    return str(tg_row[0]) if tg_row and tg_row[0] is not None else None
