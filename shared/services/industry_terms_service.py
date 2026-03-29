from typing import Dict, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.industry_term import IndustryTerm


DEFAULT_TERMS = {
    "grocery": {"object_singular": "Магазин", "object_plural": "Магазины"},
    "florist": {"object_singular": "Салон", "object_plural": "Салоны"},
    "pickup_point": {"object_singular": "ПВЗ", "object_plural": "ПВЗ"},
}


class IndustryTermsService:
    @staticmethod
    def default_terms(industry: str) -> Dict[str, str]:
        return DEFAULT_TERMS.get(industry, DEFAULT_TERMS["grocery"]).copy()

    @staticmethod
    async def get_terms(
        session: AsyncSession, industry: str, language: str = "ru"
    ) -> Dict[str, str]:
        base = IndustryTermsService.default_terms(industry)
        q = select(IndustryTerm).where(
            and_(
                IndustryTerm.industry == industry,
                IndustryTerm.language == language,
                IndustryTerm.is_active.is_(True),
            )
        )
        res = await session.execute(q)
        for item in res.scalars().all():
            base[item.term_key] = item.term_value
        return base

    @staticmethod
    async def list_terms(
        session: AsyncSession, industry: str | None = None, language: str = "ru"
    ) -> List[IndustryTerm]:
        q = select(IndustryTerm).where(IndustryTerm.language == language)
        if industry:
            q = q.where(IndustryTerm.industry == industry)
        q = q.order_by(IndustryTerm.industry, IndustryTerm.term_key)
        res = await session.execute(q)
        return res.scalars().all()

    @staticmethod
    async def upsert_term(
        session: AsyncSession,
        industry: str,
        language: str,
        term_key: str,
        term_value: str,
        source: str = "manual",
        is_active: bool = True,
    ) -> IndustryTerm:
        q = select(IndustryTerm).where(
            and_(
                IndustryTerm.industry == industry,
                IndustryTerm.language == language,
                IndustryTerm.term_key == term_key,
            )
        )
        res = await session.execute(q)
        term = res.scalar_one_or_none()
        if not term:
            term = IndustryTerm(
                industry=industry,
                language=language,
                term_key=term_key,
                term_value=term_value,
                source=source,
                is_active=is_active,
            )
            session.add(term)
        else:
            term.term_value = term_value
            term.source = source
            term.is_active = is_active
        await session.commit()
        await session.refresh(term)
        return term
