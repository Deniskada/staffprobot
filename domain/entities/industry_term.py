from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from domain.entities.base import Base


class IndustryTerm(Base):
    __tablename__ = "industry_terms"
    __table_args__ = (
        UniqueConstraint("industry", "language", "term_key", name="uq_industry_terms"),
    )

    id = Column(Integer, primary_key=True, index=True)
    industry = Column(String(50), nullable=False, index=True)
    language = Column(String(10), nullable=False, index=True, default="ru")
    term_key = Column(String(64), nullable=False, index=True)
    term_value = Column(String(255), nullable=False)
    source = Column(String(20), nullable=False, default="manual")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
