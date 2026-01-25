"""Лог изменений тарифов и опций подписки (restruct1 Фаза 1.6)."""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from .base import Base


class SubscriptionOptionLog(Base):
    """История изменений тарифа и включения/выключения опций по подписке."""

    __tablename__ = "subscription_option_log"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(
        Integer,
        ForeignKey("user_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    old_tariff_id = Column(Integer, ForeignKey("tariff_plans.id", ondelete="SET NULL"), nullable=True)
    new_tariff_id = Column(Integer, ForeignKey("tariff_plans.id", ondelete="SET NULL"), nullable=True)
    options_enabled = Column(JSON, nullable=False, default=list)  # ["secure_media_storage", ...]
    options_disabled = Column(JSON, nullable=False, default=list)

    def __repr__(self) -> str:
        return (
            f"<SubscriptionOptionLog(id={self.id}, subscription_id={self.subscription_id}, "
            f"changed_at={self.changed_at})>"
        )
