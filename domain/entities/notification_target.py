"""Целевые чаты/каналы для уведомлений (TG, MAX)."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class NotificationTarget(Base):
    """
    Целевой чат/канал для отчётов и уведомлений.

    Заменяет одиночные telegram_report_chat_id в objects и org_structure_units.
    """

    __tablename__ = "notification_targets"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(
        String(32),
        nullable=False,
        comment="object | org_unit",
    )
    scope_id = Column(Integer, nullable=False, index=True, comment="ID объекта или org_unit")
    messenger = Column(
        String(32),
        nullable=False,
        comment="telegram | max",
    )
    target_type = Column(
        String(32),
        nullable=False,
        default="group",
        comment="user_chat | group | channel",
    )
    target_chat_id = Column(String(255), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
