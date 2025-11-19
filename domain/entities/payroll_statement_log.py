"""Журнал формирования расчётных листов."""

from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Date,
    DateTime,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from domain.entities.base import Base


class PayrollStatementLog(Base):
    """Сохраняет факты генерации расчётных листов для сотрудников."""

    __tablename__ = "payroll_statement_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_role = Column(String(32), nullable=False)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    total_net = Column(Numeric(12, 2), nullable=False)
    total_paid = Column(Numeric(12, 2), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)

    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employee = relationship("User", foreign_keys=[employee_id])
    owner = relationship("User", foreign_keys=[owner_id])
    requester = relationship("User", foreign_keys=[requested_by])

    def __repr__(self) -> str:
        return (
            f"<PayrollStatementLog(id={self.id}, employee_id={self.employee_id}, "
            f"range={self.period_start}..{self.period_end}, balance={self.balance})>"
        )

