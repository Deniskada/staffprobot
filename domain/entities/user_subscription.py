"""Модель подписки пользователя на тарифный план."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone

from .base import Base


class SubscriptionStatus(enum.Enum):
    """Статус подписки."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class BillingPeriod(enum.Enum):
    """Период биллинга."""
    MONTH = "month"
    YEAR = "year"


class UserSubscription(Base):
    """Модель подписки пользователя на тарифный план."""
    
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tariff_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False, index=True)
    
    # Статус подписки
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Временные поля
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_payment_at = Column(DateTime(timezone=True), nullable=True)
    
    # Настройки
    auto_renewal = Column(Boolean, nullable=False, default=True)
    payment_method = Column(String(50), nullable=True)  # card, bank_transfer, etc.
    
    # Метаданные
    notes = Column(String(500), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="subscriptions")
    tariff_plan = relationship("TariffPlan", back_populates="subscriptions")
    
    def __repr__(self) -> str:
        return f"<UserSubscription(id={self.id}, user_id={self.user_id}, status='{self.status.value}')>"
    
    def is_expired(self) -> bool:
        """Проверка, истекла ли подписка."""
        if not self.expires_at:
            return False
        now = datetime.now(timezone.utc)
        # Убеждаемся, что оба datetime имеют timezone
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at

    def days_until_expiry(self) -> int:
        """Количество дней до истечения подписки."""
        if not self.expires_at:
            return float('inf')  # Бессрочная подписка
        now = datetime.now(timezone.utc)
        # Убеждаемся, что оба datetime имеют timezone
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = expires_at - now
        return delta.days

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tariff_plan_id": self.tariff_plan_id,
            "status": self.status.value if self.status else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_payment_at": self.last_payment_at.isoformat() if self.last_payment_at else None,
            "auto_renewal": self.auto_renewal,
            "payment_method": self.payment_method,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_active(self) -> bool:
        """Проверка активности подписки."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        
        if self.expires_at is None:
            return True  # Бессрочная подписка
        
        from datetime import datetime
        return datetime.now() <= self.expires_at
    
