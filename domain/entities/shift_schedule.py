"""Модель запланированной смены."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional
from datetime import datetime, timedelta, timezone


class ShiftSchedule(Base):
    """Модель запланированной смены."""
    
    __tablename__ = "shift_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=True, index=True)
    planned_start = Column(DateTime(timezone=True), nullable=False, index=True)
    planned_end = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="planned", index=True)  # planned, confirmed, cancelled, completed
    hourly_rate = Column(Numeric(10, 2), nullable=True)  # Ставка на момент планирования
    notes = Column(Text, nullable=True)
    notification_sent = Column(Boolean, default=False)  # Отправлено ли уведомление
    auto_closed = Column(Boolean, default=False)  # Автоматически ли закрыта смена
    actual_shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)  # Связь с фактической сменой
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    user = relationship("User", backref="scheduled_shifts")
    object = relationship("Object", backref="scheduled_shifts")
    time_slot = relationship("TimeSlot", backref="scheduled_shifts")
    actual_shift = relationship("Shift", backref="scheduled_from")
    
    def __repr__(self) -> str:
        return f"<ShiftSchedule(id={self.id}, user_id={self.user_id}, object_id={self.object_id}, status='{self.status}')>"
    
    @property
    def planned_duration_hours(self) -> float:
        """Запланированная длительность смены в часах."""
        if self.planned_start and self.planned_end:
            duration = self.planned_end - self.planned_start
            return round(duration.total_seconds() / 3600, 2)
        return 0.0
    
    @property
    def planned_payment(self) -> Optional[float]:
        """Запланированная оплата за смену."""
        if self.hourly_rate:
            return float(self.hourly_rate) * self.planned_duration_hours
        return None
    
    @property
    def is_upcoming(self) -> bool:
        """Проверка, предстоящая ли смена."""
        return self.planned_start > datetime.now(timezone.utc) and self.status == "planned"
    
    @property
    def is_today(self) -> bool:
        """Проверка, запланирована ли смена на сегодня."""
        today = datetime.now(timezone.utc).date()
        return self.planned_start.date() == today
    
    @property
    def time_until_start(self) -> Optional[timedelta]:
        """Время до начала смены."""
        if self.is_upcoming:
            return self.planned_start - datetime.now(timezone.utc)
        return None
    
    @property
    def formatted_time_range(self) -> str:
        """Форматированное время смены."""
        from core.utils.timezone_helper import timezone_helper
        
        # Конвертируем в локальное время
        local_start = timezone_helper.utc_to_local(self.planned_start)
        local_end = timezone_helper.utc_to_local(self.planned_end)
        
        start_time = local_start.strftime('%H:%M')
        end_time = local_end.strftime('%H:%M')
        date = local_start.strftime('%d.%m.%Y')
        return f"{date} {start_time}-{end_time}"
    
    def can_be_cancelled(self) -> bool:
        """Можно ли отменить смену."""
        # Смену можно отменить за час до начала
        return (
            self.status in ["planned", "confirmed"] and 
            self.time_until_start and 
            self.time_until_start > timedelta(hours=1)
        )
    
    def needs_reminder(self, hours_before: int = 2) -> bool:
        """Нужно ли отправить напоминание."""
        if not self.is_upcoming or self.notification_sent:
            return False
        
        time_until = self.time_until_start
        if not time_until:
            return False
        
        return time_until <= timedelta(hours=hours_before)
