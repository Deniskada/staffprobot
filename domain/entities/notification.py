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
    SHIFT_DID_NOT_START = "shift_did_not_start"         # Смена не состоялась
    
    # Объекты (lowercase для совместимости с новыми миграциями)
    OBJECT_OPENED = "object_opened"                     # Объект открылся вовремя
    OBJECT_CLOSED = "object_closed"                     # Объект закрылся
    OBJECT_LATE_OPENING = "object_late_opening"         # Объект открылся с опозданием
    OBJECT_NO_SHIFTS_TODAY = "object_no_shifts_today"   # На объекте нет смен сегодня
    OBJECT_EARLY_CLOSING = "object_early_closing"       # Объект закрыт раньше времени
    
    # Договоры
    CONTRACT_SIGNED = "contract_signed"                 # Договор подписан
    CONTRACT_TERMINATED = "contract_terminated"         # Договор расторгнут
    CONTRACT_EXPIRING = "contract_expiring"             # Договор истекает
    CONTRACT_UPDATED = "contract_updated"               # Договор обновлен
    
    # Оферта
    OFFER_SENT = "offer_sent"                           # Оферта направлена на подписание
    OFFER_ACCEPTED = "offer_accepted"                   # Оферта принята сотрудником
    OFFER_REJECTED = "offer_rejected"                   # Сотрудник отклонил оферту
    OFFER_TERMS_CHANGED = "offer_terms_changed"         # Условия оферты изменены
    
    # KYC / Верификация
    KYC_REQUIRED = "kyc_required"                       # Требуется верификация
    KYC_VERIFIED = "kyc_verified"                       # Верификация пройдена
    KYC_FAILED = "kyc_failed"                           # Верификация не пройдена
    
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
    
    # Задачи (lowercase для совместимости с новыми миграциями)
    TASK_ASSIGNED = "task_assigned"                     # Назначена новая задача
    TASK_COMPLETED = "task_completed"                   # Задача выполнена
    TASK_OVERDUE = "task_overdue"                       # Задача просрочена
    
    # Инциденты
    INCIDENT_CREATED = "incident_created"               # Инцидент создан
    INCIDENT_RESOLVED = "incident_resolved"             # Инцидент решён
    INCIDENT_REJECTED = "incident_rejected"             # Инцидент отклонён
    INCIDENT_CANCELLED = "incident_cancelled"           # Инцидент отменён
    
    # Сотрудники
    EMPLOYEE_BIRTHDAY = "employee_birthday"             # День рождения сотрудника
    EMPLOYEE_HOLIDAY_GREETING = "employee_holiday_greeting"  # Поздравление с государственным праздником

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
    SCHEDULED = "scheduled"       # Запланировано
    SENT = "sent"                 # Отправлено
    DELIVERED = "delivered"       # Доставлено
    FAILED = "failed"             # Не удалось отправить
    READ = "read"                 # Прочитано
    CANCELLED = "cancelled"       # Отменено
    DELETED = "deleted"           # Удалено (мягкое удаление)


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
    # Используем String вместо Enum для совместимости с БД, где хранятся значения (строки)
    type = Column(String(50), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    
    # Статус и приоритет
    status = Column(String(20), nullable=False, default=NotificationStatus.PENDING.name, index=True)
    priority = Column(String(20), nullable=False, default=NotificationPriority.NORMAL.name)
    
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
    
    @property
    def type_enum(self) -> NotificationType:
        """Конвертация строки type в enum."""
        if isinstance(self.type, NotificationType):
            return self.type
        try:
            # Пробуем найти по значению (object_no_shifts_today)
            for nt in NotificationType:
                if nt.value == self.type:
                    return nt
            # Если не нашли по значению, пробуем по имени (OBJECT_NO_SHIFTS_TODAY)
            return NotificationType[self.type.upper()]
        except (KeyError, AttributeError):
            raise ValueError(f"Unknown notification type: {self.type}")
    
    @property
    def channel_enum(self) -> NotificationChannel:
        """Конвертация строки channel в enum."""
        if isinstance(self.channel, NotificationChannel):
            return self.channel
        try:
            for nc in NotificationChannel:
                if nc.value == self.channel or nc.name == self.channel:
                    return nc
            return NotificationChannel[self.channel.upper()]
        except (KeyError, AttributeError):
            raise ValueError(f"Unknown notification channel: {self.channel}")
    
    @property
    def status_enum(self) -> NotificationStatus:
        """Конвертация строки status в enum."""
        if isinstance(self.status, NotificationStatus):
            return self.status
        try:
            for ns in NotificationStatus:
                if ns.value == self.status or ns.name == self.status:
                    return ns
            return NotificationStatus[self.status.upper()]
        except (KeyError, AttributeError):
            raise ValueError(f"Unknown notification status: {self.status}")
    
    @property
    def priority_enum(self) -> NotificationPriority:
        """Конвертация строки priority в enum."""
        if isinstance(self.priority, NotificationPriority):
            return self.priority
        try:
            for np in NotificationPriority:
                if np.value == self.priority or np.name == self.priority:
                    return np
            return NotificationPriority[self.priority.upper()]
        except (KeyError, AttributeError):
            raise ValueError(f"Unknown notification priority: {self.priority}")
    
    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type='{self.type}', channel='{self.channel}', "
            f"status='{self.status}')>"
        )
    
    def is_scheduled(self) -> bool:
        """Проверка, запланировано ли уведомление на будущее."""
        if not self.scheduled_at or self.status_enum != NotificationStatus.PENDING:
            return False
        now = datetime.now(timezone.utc)
        scheduled_at = self.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        return scheduled_at > now
    
    def is_overdue(self) -> bool:
        """Проверка, просрочено ли уведомление."""
        if not self.scheduled_at or self.status_enum != NotificationStatus.PENDING:
            return False
        now = datetime.now(timezone.utc)
        scheduled_at = self.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        return scheduled_at < now
    
    def is_read(self) -> bool:
        """Проверка, прочитано ли уведомление."""
        return self.read_at is not None or self.status_enum == NotificationStatus.READ
    
    def is_urgent(self) -> bool:
        """Проверка, является ли уведомление срочным."""
        return self.priority_enum == NotificationPriority.URGENT
    
    def mark_as_sent(self, sent_at: Optional[datetime] = None) -> None:
        """Отметить как отправленное."""
        self.status = NotificationStatus.SENT.name  # Сохраняем имя enum в БД
        self.sent_at = sent_at or datetime.now(timezone.utc)
    
    def mark_as_delivered(self) -> None:
        """Отметить как доставленное."""
        self.status = NotificationStatus.DELIVERED.name  # Сохраняем имя enum в БД
    
    def mark_as_read(self, read_at: Optional[datetime] = None) -> None:
        """Отметить как прочитанное."""
        self.status = NotificationStatus.READ.name  # Сохраняем имя enum в БД
        self.read_at = read_at or datetime.now(timezone.utc)
    
    def mark_as_failed(self, error_message: Optional[str] = None) -> None:
        """Отметить как неудавшееся."""
        self.status = NotificationStatus.FAILED.name  # Сохраняем имя enum в БД
        self.error_message = error_message
        self.retry_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        # type, channel, status, priority - это строки (из-за native_enum=False)
        # Используем их напрямую, если это строки, иначе через .value
        type_str = self.type if isinstance(self.type, str) else self.type.value
        channel_str = self.channel if isinstance(self.channel, str) else self.channel.value
        status_str = self.status if isinstance(self.status, str) else self.status.value
        priority_str = self.priority if isinstance(self.priority, str) else self.priority.value
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": type_str,
            "channel": channel_str,
            "status": status_str,
            "priority": priority_str,
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

