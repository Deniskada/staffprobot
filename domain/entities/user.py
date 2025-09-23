"""Модель пользователя."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """Роли пользователей."""
    OWNER = "owner"
    EMPLOYEE = "employee" 
    APPLICANT = "applicant"
    MANAGER = "manager"
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
    email = Column(String(255), nullable=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    work_experience = Column(String(50), nullable=True)
    education = Column(String(50), nullable=True)
    skills = Column(String(1000), nullable=True)
    about = Column(String(2000), nullable=True)
    preferred_schedule = Column(String(50), nullable=True)
    preferred_work_types = Column(JSONB, nullable=True)  # Предпочитаемые типы работы
    min_salary = Column(Integer, nullable=True)
    availability_notes = Column(String(1000), nullable=True)
    role = Column(String(50), nullable=False)  # Оставляем для обратной совместимости
    roles = Column(JSONB, nullable=False)  # Новое поле для множественных ролей
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
        if hasattr(self, 'roles') and self.roles:
            return UserRole.OWNER.value in self.roles
        return self.role == UserRole.OWNER.value
    
    def is_employee(self) -> bool:
        """Проверка, является ли пользователь сотрудником."""
        if hasattr(self, 'roles') and self.roles:
            return UserRole.EMPLOYEE.value in self.roles
        return self.role == UserRole.EMPLOYEE.value
    
    def is_applicant(self) -> bool:
        """Проверка, является ли пользователь соискателем."""
        if hasattr(self, 'roles') and self.roles:
            return UserRole.APPLICANT.value in self.roles
        return self.role == UserRole.APPLICANT.value
    
    def is_manager(self) -> bool:
        """Проверка, является ли пользователь управляющим."""
        if hasattr(self, 'roles') and self.roles:
            return UserRole.MANAGER.value in self.roles
        return self.role == UserRole.MANAGER.value
    
    def is_superadmin(self) -> bool:
        """Проверка, является ли пользователь суперадмином."""
        if hasattr(self, 'roles') and self.roles:
            return UserRole.SUPERADMIN.value in self.roles
        return self.role == UserRole.SUPERADMIN.value
    
    def has_role(self, role: UserRole) -> bool:
        """Проверка, имеет ли пользователь указанную роль."""
        # Поддерживаем как старый формат (role), так и новый (roles)
        if hasattr(self, 'roles') and self.roles:
            return role.value in self.roles
        return self.role == role.value
    
    def can_manage_objects(self) -> bool:
        """Проверка, может ли пользователь управлять объектами."""
        if hasattr(self, 'roles') and self.roles:
            return any(role in self.roles for role in [UserRole.OWNER.value, UserRole.SUPERADMIN.value])
        return self.role in [UserRole.OWNER.value, UserRole.SUPERADMIN.value]
    
    def can_manage_users(self) -> bool:
        """Проверка, может ли пользователь управлять пользователями."""
        if hasattr(self, 'roles') and self.roles:
            return any(role in self.roles for role in [UserRole.OWNER.value, UserRole.SUPERADMIN.value])
        return self.role in [UserRole.OWNER.value, UserRole.SUPERADMIN.value]
    
    def can_work_shifts(self) -> bool:
        """Проверка, может ли пользователь работать сменами."""
        if hasattr(self, 'roles') and self.roles:
            return any(role in self.roles for role in [UserRole.EMPLOYEE.value, UserRole.OWNER.value, UserRole.SUPERADMIN.value])
        return self.role in [UserRole.EMPLOYEE.value, UserRole.OWNER.value, UserRole.SUPERADMIN.value]
    
    def add_role(self, role: UserRole) -> bool:
        """Добавление роли пользователю."""
        if not hasattr(self, 'roles') or not self.roles:
            self.roles = [self.role] if self.role else []
        
        if role.value not in self.roles:
            self.roles.append(role.value)
            return True
        return False
    
    def remove_role(self, role: UserRole) -> bool:
        """Удаление роли у пользователя."""
        if not hasattr(self, 'roles') or not self.roles:
            return False
        
        if role.value in self.roles:
            self.roles.remove(role.value)
            return True
        return False
    
    def get_roles(self) -> list:
        """Получение списка ролей пользователя."""
        if hasattr(self, 'roles') and self.roles:
            return self.roles
        return [self.role] if self.role else []
    
    # Связи
    owner_profile = relationship("OwnerProfile", back_populates="user", uselist=False)
    
    # Связи с заявками и собеседованиями
    applications = relationship("Application", back_populates="applicant", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="applicant", cascade="all, delete-orphan")





