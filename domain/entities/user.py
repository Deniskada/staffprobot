"""Модель пользователя."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from .base import Base
from datetime import datetime
from typing import Optional


class User(Base):
    """Модель пользователя."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), nullable=False, default="employee")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def is_owner(self) -> bool:
        """Проверка, является ли пользователь владельцем."""
        return self.role == "owner"
    
    def is_manager(self) -> bool:
        """Проверка, является ли пользователь менеджером."""
        return self.role in ["owner", "manager"]
    
    def is_employee(self) -> bool:
        """Проверка, является ли пользователь сотрудником."""
        return self.role == "employee"





