"""Сервис политик причин отмены смен по владельцу."""

from typing import List, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.cancellation_reason import CancellationReason


class CancellationPolicyService:
    """Загрузка причин отмен из БД с учетом владельца и фолбэком на глобальные."""

    @staticmethod
    async def get_owner_reasons(
        session: AsyncSession,
        owner_id: int,
        only_visible: bool = True,
        only_active: bool = True,
    ) -> List[CancellationReason]:
        """Вернуть причины для владельца, если отсутствуют — вернуть глобальные (owner_id IS NULL)."""
        query = select(CancellationReason).where(CancellationReason.owner_id == owner_id)
        if only_visible:
            query = query.where(CancellationReason.is_employee_visible == True)  # noqa: E712
        if only_active:
            query = query.where(CancellationReason.is_active == True)  # noqa: E712
        query = query.order_by(CancellationReason.order_index, CancellationReason.id)

        result = await session.execute(query)
        reasons = result.scalars().all()
        if reasons:
            return reasons

        # Фолбэк: глобальные
        query_global = select(CancellationReason).where(CancellationReason.owner_id.is_(None))
        if only_visible:
            query_global = query_global.where(CancellationReason.is_employee_visible == True)  # noqa: E712
        if only_active:
            query_global = query_global.where(CancellationReason.is_active == True)  # noqa: E712
        query_global = query_global.order_by(CancellationReason.order_index, CancellationReason.id)

        result_global = await session.execute(query_global)
        return result_global.scalars().all()

    @staticmethod
    async def get_reason_map(
        session: AsyncSession,
        owner_id: int,
        include_inactive: bool = True,
        include_hidden: bool = True,
    ) -> Dict[str, CancellationReason]:
        """Карта code -> CancellationReason для владельца с фолбэком на глобальные."""
        query = select(CancellationReason).where(CancellationReason.owner_id == owner_id)
        if not include_inactive:
            query = query.where(CancellationReason.is_active == True)  # noqa: E712
        if not include_hidden:
            query = query.where(CancellationReason.is_employee_visible == True)  # noqa: E712
        result = await session.execute(query)
        reasons = {r.code: r for r in result.scalars().all()}

        # Дополнить глобальными, если кода нет у владельца
        query_global = select(CancellationReason).where(CancellationReason.owner_id.is_(None))
        if not include_inactive:
            query_global = query_global.where(CancellationReason.is_active == True)  # noqa: E712
        if not include_hidden:
            query_global = query_global.where(CancellationReason.is_employee_visible == True)  # noqa: E712
        result_global = await session.execute(query_global)
        for gr in result_global.scalars().all():
            reasons.setdefault(gr.code, gr)

        return reasons


