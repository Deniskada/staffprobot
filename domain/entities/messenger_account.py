"""Привязки мессенджеров и OAuth к user_id."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class MessengerAccount(Base):
    """
    Привязка внешнего аккаунта (TG, MAX, OAuth) к пользователю.

    UNIQUE(provider, external_user_id) — один внешний аккаунт = один user_id (Auth-дубли).
    """

    __tablename__ = "messenger_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(
        String(50),
        nullable=False,
        comment="telegram | max | yandex_id | tinkoff_id",
    )
    external_user_id = Column(String(255), nullable=False, comment="ID в системе провайдера")
    chat_id = Column(String(255), nullable=True, comment="TG/MAX chat_id")
    username = Column(String(255), nullable=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "external_user_id", name="uq_messenger_provider_external"),
        UniqueConstraint("user_id", "provider", name="uq_messenger_user_provider"),
    )

    user = relationship("User", backref="messenger_accounts")
