"""Модель открытия/закрытия объекта."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional
from datetime import datetime


class ObjectOpening(Base):
    """Модель открытия/закрытия объекта.
    
    Отслеживает когда объект был открыт и закрыт, кем и с какими координатами.
    Активная запись (closed_at IS NULL) означает что объект открыт.
    """
    
    __tablename__ = "object_openings"
    
    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id", ondelete="CASCADE"), nullable=False, index=True)
    opened_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    open_coordinates = Column(String(100), nullable=True)  # "lat,lon" формат
    closed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    close_coordinates = Column(String(100), nullable=True)  # "lat,lon" формат
    
    # Отношения
    object = relationship("Object", backref="openings")
    opener = relationship("User", foreign_keys=[opened_by], backref="opened_objects")
    closer = relationship("User", foreign_keys=[closed_by], backref="closed_objects")
    
    __table_args__ = (
        Index('ix_object_openings_active', object_id, closed_at),
        Index('ix_object_openings_opened_at', opened_at),
    )
    
    def __repr__(self) -> str:
        status = "открыт" if self.closed_at is None else "закрыт"
        return f"<ObjectOpening(id={self.id}, object_id={self.object_id}, {status})>"
    
    @property
    def is_open(self) -> bool:
        """Проверка: открыт ли объект."""
        return self.closed_at is None
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Длительность открытия в часах."""
        if not self.closed_at:
            return None
        delta = self.closed_at - self.opened_at
        return round(delta.total_seconds() / 3600, 2)

