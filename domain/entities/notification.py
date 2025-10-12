"""Универсальная модель уведомлений."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .base import Base


class NotificationType(enum.Enum):
    """Тип уведомления."""
    # Смены
    SHIFT_REMINDER = "shift_reminder"                   # Напоминание о смене
    SHIFT_CONFIRMED = "shift_confirmed"                 # Смена подтверждена
    SHIFT_CANCELLED = "shift_cancelled"                 # Смена отменена
    SHIFT_STARTED = "shift_started"                     # Смена началась
    SHIFT_COMPLETED = "shift_completed"                 # Смена завершена
    
    # Договоры
    CONTRACT_SIGNED = "contract_signed"                 # Договор подписан
    CONTRACT_TERMINATED = "contract_terminated"         # Договор расторгнут
    CONTRACT_EXPIRING = "contract_expiring"             # Договор истекает
    CONTRACT_UPDATED = "contract_updated"               # Договор обновлен
    
    # Отзывы
    REVIEW_RECEIVED = "review_received"                 # Получен отзыв
    REVIEW_MODERATED = "review_moderated"               # Отзыв промодерирован
    APPEAL_SUBMITTED = "appeal_submitted"               # Подано обжалование
    APPEAL_DECISION = "appeal_decision"                 # Решение по обжалованию
    
    # Платежи
    PAYMENT_DUE = "payment_due"                         # Предстоящий платеж
    PAYMENT_SUCCESS = "payment_success"                 # Успешный платеж
    PAYMENT_FAILED = "payment_failed"                   # Неудачный платеж
    SUBSCRIPTION_EXPIRING = "subscription_expiring"     # Подписка истекает
    SUBSCRIPTION_EXPIRED = "subscription_expired"       # Подписка истекла
    USAGE_LIMIT_WARNING = "usage_limit_warning"         # Предупреждение о лимите
    USAGE_LIMIT_EXCEEDED = "usage_limit_exceeded"       # Лимит превышен
    
    # Системные
    WELCOME = "welcome"                                 # Приветствие
    PASSWORD_RESET = "password_reset"                   # Сброс пароля
    ACCOUNT_SUSPENDED = "account_suspended"             # Аккаунт заблокирован
    ACCOUNT_ACTIVATED = "account_activated"             # Аккаунт активирован
    SYSTEM_MAINTENANCE = "system_maintenance"           # Системное обслуживание
    FEATURE_ANNOUNCEMENT = "feature_announcement"       # Анонс новой функции


class NotificationStatus(enum.Enum):
    """Статус уведомления."""
    PENDING = "pending"           # Ожидает отправки
    SENT = "sent"                 # Отправлено
    DELIVERED = "delivered"       # Доставлено
    FAILED = "failed"             # Не удалось отправить
    READ = "read"                 # Прочитано
    CANCELLED = "cancelled"       # Отменено


class NotificationChannel(enum.Enum):
    """Канал отправки уведомления."""
    EMAIL = "email"               # Email
    SMS = "sms"                   # SMS
    PUSH = "push"                 # Web Push
    TELEGRAM = "telegram"         # Telegram
    IN_APP = "in_app"             # В приложении
    WEBHOOK = "webhook"           # Webhook
    SLACK = "slack"               # Slack
    DISCORD = "discord"           # Discord


class NotificationPriority(enum.Enum):
    """Приоритет уведомления."""
    LOW = "low"                   # Низкий (дайджесты, новости)
    NORMAL = "normal"             # Обычный (большинство уведомлений)
    HIGH = "high"                 # Высокий (важные события)
    URGENT = "urgent"             # Срочный (критичные, не ограничиваются rate limit)


class Notification(Base):
    """Универсальная модель уведомления."""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Тип и канал
    type = Column(Enum(NotificationType), nullable=False, index=True)
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    # Статус и приоритет
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING, index=True)
    priority = Column(Enum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL)
    
    # Содержимое
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Дополнительные данные (object_id, shift_id, etc.)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Время планируемой отправки
    sent_at = Column(DateTime(timezone=True), nullable=True)                   # Время фактической отправки
    read_at = Column(DateTime(timezone=True), nullable=True)                   # Время прочтения
    
    # Метаданные
    error_message = Column(Text, nullable=True)      # Сообщение об ошибке (если failed)
    retry_count = Column(Integer, nullable=False, default=0)  # Количество попыток отправки
    
    # Связанные объекты
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type='{self.type.value}', channel='{self.channel.value}', "
            f"status='{self.status.value}')>"
        )
    
    def is_scheduled(self) -> bool:
        """Проверка, запланировано ли уведомление на будущее."""
        if not self.scheduled_at or self.status != NotificationStatus.PENDING:
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
    
    def is_read(self) -> bool:
        """Проверка, прочитано ли уведомление."""
        return self.read_at is not None or self.status == NotificationStatus.READ
    
    def is_urgent(self) -> bool:
        """Проверка, является ли уведомление срочным."""
        return self.priority == NotificationPriority.URGENT
    
    def mark_as_sent(self, sent_at: Optional[datetime] = None) -> None:
        """Отметить как отправленное."""
        self.status = NotificationStatus.SENT
        self.sent_at = sent_at or datetime.now(timezone.utc)
    
    def mark_as_delivered(self) -> None:
        """Отметить как доставленное."""
        self.status = NotificationStatus.DELIVERED
    
    def mark_as_read(self, read_at: Optional[datetime] = None) -> None:
        """Отметить как прочитанное."""
        self.status = NotificationStatus.READ
        self.read_at = read_at or datetime.now(timezone.utc)
    
    def mark_as_failed(self, error_message: Optional[str] = None) -> None:
        """Отметить как неудавшееся."""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value,
            "channel": self.channel.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "is_scheduled": self.is_scheduled(),
            "is_overdue": self.is_overdue(),
            "is_read": self.is_read(),
            "is_urgent": self.is_urgent(),
        }

