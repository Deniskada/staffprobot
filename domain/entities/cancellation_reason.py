"""Модель причин отмены смен (настраивается владельцем)."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class CancellationReason(Base):
    __tablename__ = "cancellation_reasons"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    code = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)

    requires_document = Column(Boolean, nullable=False, default=False)
    treated_as_valid = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_employee_visible = Column(Boolean, nullable=False, default=True)
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        UniqueConstraint("owner_id", "code", name="uq_cancellation_reasons_owner_code"),
    )

    def __repr__(self) -> str:
        return f"<CancellationReason(owner_id={self.owner_id}, code='{self.code}', active={self.is_active})>"


