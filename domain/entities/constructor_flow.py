"""Модели конструктора шаблонов договоров: flow, steps, fragments."""

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from domain.entities.base import Base


class ConstructorFlow(Base):
    """Мастер конструктора шаблона для типа договора."""

    __tablename__ = "constructor_flows"

    id = Column(Integer, primary_key=True, index=True)
    contract_type_id = Column(Integer, ForeignKey("contract_types.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True, nullable=False)
    source = Column(String(32), nullable=False, default="manual")
    source_metadata = Column(JSON, nullable=True)

    contract_type = relationship("ContractType", backref="constructor_flows")
    steps = relationship("ConstructorStep", back_populates="flow", order_by="ConstructorStep.sort_order")


class ConstructorStep(Base):
    """Шаг мастера конструктора."""

    __tablename__ = "constructor_steps"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("constructor_flows.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(128), nullable=False)
    schema = Column(JSON, nullable=True)
    request_at_conclusion = Column(Boolean, default=False, nullable=False)

    flow = relationship("ConstructorFlow", back_populates="steps")
    fragments = relationship("ConstructorFragment", back_populates="step", cascade="all, delete-orphan")


class ConstructorFragment(Base):
    """Фрагмент текста договора для шага и (опционально) варианта выбора."""

    __tablename__ = "constructor_fragments"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("constructor_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    option_key = Column(String(128), nullable=True)
    fragment_content = Column(Text, nullable=False)

    step = relationship("ConstructorStep", back_populates="fragments")
