"""Модель объекта."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from .base import Base
from sqlalchemy.orm import relationship
from typing import Optional




class Object(Base):
    """Модель объекта."""
    
    __tablename__ = "objects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address = Column(Text, nullable=True)
    coordinates = Column(String(100), nullable=False)  # "lat,lon" формат для MVP
    opening_time = Column(Time, nullable=False)
    closing_time = Column(Time, nullable=False)
    hourly_rate = Column(Numeric(10, 2), nullable=False)
    required_employees = Column(Text, nullable=True)  # JSON строка для MVP
    max_distance_meters = Column(Integer, nullable=False, default=500)  # Максимальное расстояние для геолокации
    auto_close_minutes = Column(Integer, nullable=False, default=60)  # Автоматическое закрытие смен через N минут
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    owner = relationship("User", backref="owned_objects")
    
    def __repr__(self) -> str:
        return f"<Object(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"
    
    @property
    def working_hours(self) -> str:
        """Время работы объекта в читаемом формате."""
        return f"{self.opening_time.strftime('%H:%M')} - {self.closing_time.strftime('%H:%M')}"
    
    def is_working_now(self) -> bool:
        """Проверка, работает ли объект сейчас."""
        from datetime import datetime, time
        now = datetime.now().time()
        return self.opening_time <= now <= self.closing_time
    
    def get_coordinates_tuple(self) -> tuple[float, float]:
        """Получение координат в виде кортежа."""
        try:
            lat, lon = self.coordinates.split(',')
            return float(lat.strip()), float(lon.strip())
        except (ValueError, AttributeError):
            return (0.0, 0.0)
    
    def set_coordinates(self, lat: float, lon: float) -> None:
        """Установка координат."""
        self.coordinates = f"{lat},{lon}"





