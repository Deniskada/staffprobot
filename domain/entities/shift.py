"""Модель смены."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional
from datetime import datetime


class Shift(Base):
    """Модель смены."""
    
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=True, index=True)
    schedule_id = Column(Integer, ForeignKey("shift_schedules.id"), nullable=True, index=True)  # Связь с планированием
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="active", index=True)  # active, completed, cancelled
    is_planned = Column(Boolean, default=False)  # Была ли смена запланирована
    start_coordinates = Column(String(100), nullable=True)  # "lat,lon" формат для MVP
    end_coordinates = Column(String(100), nullable=True)  # "lat,lon" формат для MVP
    total_hours = Column(Numeric(5, 2), nullable=True)
    hourly_rate = Column(Numeric(10, 2), nullable=True)
    total_payment = Column(Numeric(10, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    user = relationship("User", backref="shifts")
    object = relationship("Object", backref="shifts")
    time_slot = relationship("TimeSlot", backref="shifts")
    schedule = relationship("ShiftSchedule", backref="actual_shifts")  # Связь с планированием
    
    def __repr__(self) -> str:
        return f"<Shift(id={self.id}, user_id={self.user_id}, object_id={self.object_id}, status='{self.status}')>"
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Длительность смены в часах."""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            return round(duration.total_seconds() / 3600, 2)
        return None
    
    @property
    def is_active(self) -> bool:
        """Проверка, активна ли смена."""
        return self.status == "active"
    
    @property
    def is_completed(self) -> bool:
        """Проверка, завершена ли смена."""
        return self.status == "completed"
    
    def calculate_payment(self) -> Optional[float]:
        """Расчет оплаты за смену."""
        if self.hourly_rate and self.duration_hours:
            return round(float(self.hourly_rate) * self.duration_hours, 2)
        return None
    
    def get_start_coordinates_tuple(self) -> Optional[tuple[float, float]]:
        """Получение координат начала в виде кортежа."""
        if not self.start_coordinates:
            return None
        try:
            lat, lon = self.start_coordinates.split(',')
            return float(lat.strip()), float(lon.strip())
        except (ValueError, AttributeError):
            return None
    
    def get_end_coordinates_tuple(self) -> Optional[tuple[float, float]]:
        """Получение координат окончания в виде кортежа."""
        if not self.end_coordinates:
            return None
        try:
            lat, lon = self.end_coordinates.split(',')
            return float(lat.strip()), float(lon.strip())
        except (ValueError, AttributeError):
            return None
    
    def set_start_coordinates(self, lat: float, lon: float) -> None:
        """Установка координат начала смены."""
        self.start_coordinates = f"{lat},{lon}"
    
    def set_end_coordinates(self, lat: float, lon: float) -> None:
        """Установка координат окончания смены."""
        self.end_coordinates = f"{lat},{lon}"
    
    def complete_shift(self, end_time: Optional[datetime] = None, 
                      end_coordinates: Optional[tuple[float, float]] = None) -> None:
        """Завершение смены."""
        self.end_time = end_time or datetime.now()
        if end_coordinates:
            self.set_end_coordinates(*end_coordinates)
        self.status = "completed"
        
        # Расчет оплаты
        if self.hourly_rate:
            self.total_hours = self.duration_hours
            self.total_payment = self.calculate_payment()





