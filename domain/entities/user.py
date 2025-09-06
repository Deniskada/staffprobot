"""Модель пользователя."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from .base import Base
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """Роли пользователей."""
    OWNER = "owner"
    EMPLOYEE = "employee" 
    APPLICANT = "applicant"
    SUPERADMIN = "superadmin"


class User(Base):
    """Модель пользователя."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), nullable=False, default=UserRole.EMPLOYEE)
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
        return self.role == UserRole.OWNER
    
    def is_employee(self) -> bool:
        """Проверка, является ли пользователь сотрудником."""
        return self.role == UserRole.EMPLOYEE
    
    def is_applicant(self) -> bool:
        """Проверка, является ли пользователь соискателем."""
        return self.role == UserRole.APPLICANT
    
    def is_superadmin(self) -> bool:
        """Проверка, является ли пользователь суперадмином."""
        return self.role == UserRole.SUPERADMIN
    
    def has_role(self, role: UserRole) -> bool:
        """Проверка, имеет ли пользователь указанную роль."""
        return self.role == role
    
    def can_manage_objects(self) -> bool:
        """Проверка, может ли пользователь управлять объектами."""
        return self.role in [UserRole.OWNER, UserRole.SUPERADMIN]
    
    def can_manage_users(self) -> bool:
        """Проверка, может ли пользователь управлять пользователями."""
        return self.role in [UserRole.OWNER, UserRole.SUPERADMIN]
    
    def can_work_shifts(self) -> bool:
        """Проверка, может ли пользователь работать сменами."""
        return self.role in [UserRole.EMPLOYEE, UserRole.OWNER]





