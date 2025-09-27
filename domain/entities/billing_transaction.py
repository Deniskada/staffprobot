"""Модель транзакции биллинга."""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone

from .base import Base


class TransactionType(enum.Enum):
    """Тип транзакции."""
    PAYMENT = "payment"           # Платеж за подписку
    REFUND = "refund"             # Возврат средств
    CREDIT = "credit"             # Кредит/бонус
    DEBIT = "debit"               # Списание
    ADJUSTMENT = "adjustment"     # Корректировка


class TransactionStatus(enum.Enum):
    """Статус транзакции."""
    PENDING = "pending"           # Ожидает обработки
    PROCESSING = "processing"     # В обработке
    COMPLETED = "completed"       # Завершена
    FAILED = "failed"             # Не удалась
    CANCELLED = "cancelled"       # Отменена
    REFUNDED = "refunded"         # Возвращена


class PaymentMethod(enum.Enum):
    """Способ оплаты."""
    CARD = "card"                 # Банковская карта
    BANK_TRANSFER = "bank_transfer"  # Банковский перевод
    CASH = "cash"                 # Наличные
    MANUAL = "manual"             # Ручное назначение
    STRIPE = "stripe"             # Stripe
    YOOKASSA = "yookassa"         # ЮKassa


class BillingTransaction(Base):
    """Транзакция биллинга."""
    
    __tablename__ = "billing_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    
    # Основные данные транзакции
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    amount = Column(Numeric(10, 2), nullable=False)  # Сумма в копейках
    currency = Column(String(3), nullable=False, default="RUB")
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    
    # Описание и детали
    description = Column(Text, nullable=True)
    external_id = Column(String(100), nullable=True, unique=True)  # ID в платежной системе
    gateway_response = Column(Text, nullable=True)  # Ответ от платежного шлюза
    
    # Даты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Срок действия платежа
    
    # Связанные объекты
    user = relationship("User", back_populates="billing_transactions")
    subscription = relationship("UserSubscription", back_populates="billing_transactions")
    payment_notifications = relationship("PaymentNotification", back_populates="transaction")
    
    def __repr__(self) -> str:
        return f"<BillingTransaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, status='{self.status.value}')>"
    
    def is_expired(self) -> bool:
        """Проверка, истек ли срок действия платежа."""
        if not self.expires_at:
            return False
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now > expires_at
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "transaction_type": self.transaction_type.value if self.transaction_type else None,
            "status": self.status.value if self.status else None,
            "amount": float(self.amount) if self.amount else 0,
            "currency": self.currency,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "description": self.description,
            "external_id": self.external_id,
            "gateway_response": self.gateway_response,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
