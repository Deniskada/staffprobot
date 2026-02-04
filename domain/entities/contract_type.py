"""Типы договоров (справочник)."""

from sqlalchemy import Column, Integer, String, Text
from domain.entities.base import Base


class ContractType(Base):
    """Тип договора: подряд, услуги, трудовой, устный и т.д."""

    __tablename__ = "contract_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    full_body = Column(Text, nullable=True)  # Полный текст договора с плейсхолдерами Jinja2
