"""Модель уведомлений о платежах."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone

from .base import Base


class NotificationType(enum.Enum):
    """Тип уведомления о платеже."""
    PAYMENT_DUE = "payment_due"           # Предстоящий платеж
    PAYMENT_SUCCESS = "payment_success"   # Успешный платеж
    PAYMENT_FAILED = "payment_failed"     # Неудачный платеж
    SUBSCRIPTION_EXPIRING = "subscription_expiring"  # Подписка истекает
    SUBSCRIPTION_EXPIRED = "subscription_expired"    # Подписка истекла
    USAGE_LIMIT_WARNING = "usage_limit_warning"      # Предупреждение о лимите
    USAGE_LIMIT_EXCEEDED = "usage_limit_exceeded"    # Лимит превышен


class NotificationStatus(enum.Enum):
    """Статус уведомления."""
    PENDING = "pending"           # Ожидает отправки
    SENT = "sent"                 # Отправлено
    DELIVERED = "delivered"       # Доставлено
    FAILED = "failed"             # Не удалось отправить
    READ = "read"                 # Прочитано


class NotificationChannel(enum.Enum):
    """Канал отправки уведомления."""
    EMAIL = "email"               # Email
    TELEGRAM = "telegram"         # Telegram
    SMS = "sms"                   # SMS
    WEBHOOK = "webhook"           # Webhook
    IN_APP = "in_app"             # В приложении


class PaymentNotification(Base):
    """Уведомление о платеже."""
    
    __tablename__ = "payment_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    transaction_id = Column(Integer, ForeignKey("billing_transactions.id"), nullable=True, index=True)
    
    # Основные данные
    notification_type = Column(Enum(NotificationType), nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING)
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    # Содержимое уведомления
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_data = Column(Text, nullable=True)  # Дополнительные данные в JSON
    
    # Временные метки
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # Время планируемой отправки
    sent_at = Column(DateTime(timezone=True), nullable=True)      # Время фактической отправки
    read_at = Column(DateTime(timezone=True), nullable=True)      # Время прочтения
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связанные объекты
    user = relationship("User", back_populates="payment_notifications")
    subscription = relationship("UserSubscription", back_populates="payment_notifications")
    transaction = relationship("BillingTransaction", back_populates="payment_notifications")
    
    def __repr__(self) -> str:
        return f"<PaymentNotification(id={self.id}, user_id={self.user_id}, type='{self.notification_type.value}', status='{self.status.value}')>"
    
    def is_scheduled(self) -> bool:
        """Проверка, запланировано ли уведомление на будущее."""
        if not self.scheduled_at:
            return False
        now = datetime.now(timezone.utc)
        scheduled_at = self.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        return scheduled_at > now
    
    def is_overdue(self) -> bool:
        """Проверка, просрочено ли уведомление."""
        if not self.scheduled_at or self.status != NotificationStatus.PENDING:
            return False
        now = datetime.now(timezone.utc)
        scheduled_at = self.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        return scheduled_at < now
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "transaction_id": self.transaction_id,
            "notification_type": self.notification_type.value if self.notification_type else None,
            "status": self.status.value if self.status else None,
            "channel": self.channel.value if self.channel else None,
            "title": self.title,
            "message": self.message,
            "notification_data": self.notification_data,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_scheduled": self.is_scheduled(),
            "is_overdue": self.is_overdue(),
        }
