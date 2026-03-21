"""Резолвер пользователя для TG/MAX — internal_user_id и telegram_id для legacy-сервисов."""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.entities.messenger_account import MessengerAccount
from core.database.session import get_async_session


async def resolve_to_internal_user_id(
    provider: str,
    external_user_id: str,
    session: Optional[AsyncSession] = None,
) -> Optional[int]:
    """
    (provider, external_user_id) → internal user_id.
    Для telegram: external = telegram_id, ищем User.telegram_id или messenger_accounts.
    Для max: messenger_accounts (provider=max, external_user_id).
    """
    async def _do(sess: AsyncSession) -> Optional[int]:
        if provider == "max":
            stmt = select(MessengerAccount.user_id).where(
                MessengerAccount.provider == "max",
                MessengerAccount.external_user_id == str(external_user_id),
            )
            r = await sess.execute(stmt)
            row = r.scalar_one_or_none()
            return int(row) if row is not None else None
        if provider == "telegram":
            try:
                tid = int(external_user_id)
            except (ValueError, TypeError):
                return None
            stmt = select(User.id).where(User.telegram_id == tid)
            r = await sess.execute(stmt)
            row = r.scalar_one_or_none()
            if row is not None:
                return int(row)
            stmt_ma = select(MessengerAccount.user_id).where(
                MessengerAccount.provider == "telegram",
                MessengerAccount.external_user_id == str(tid),
            )
            r2 = await sess.execute(stmt_ma)
            row2 = r2.scalar_one_or_none()
            return int(row2) if row2 is not None else None
        return None

    if session:
        return await _do(session)
    async with get_async_session() as sess:
        return await _do(sess)


async def resolve_for_services(
    provider: str,
    external_user_id: str,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Возвращает (internal_user_id, telegram_id_for_legacy).
    telegram_id_for_legacy: для вызова сервисов, ожидающих telegram_id (User.telegram_id).
    Если у пользователя нет telegram_id — второй элемент None.
    """
    async with get_async_session() as session:
        internal_id = await resolve_to_internal_user_id(
            provider, external_user_id, session
        )
        if not internal_id:
            return (None, None)
        stmt = select(User.telegram_id).where(User.id == internal_id)
        r = await session.execute(stmt)
        row = r.scalar_one_or_none()
        telegram_id = int(row) if row is not None else None
        return (internal_id, telegram_id)
