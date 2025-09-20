"""Модели для системы договоров."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base


class ContractTemplate(Base):
    """Шаблон договора."""
    
    __tablename__ = "contract_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)  # HTML/текст шаблона
    version = Column(String(50), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Новые поля
    is_public = Column(Boolean, default=False, nullable=False)
    fields_schema = Column(JSON, nullable=True)  # [{key,label,type,required,options}]
    
    # Отношения
    creator = relationship("User", backref="created_templates")
    contracts = relationship("Contract", back_populates="template")


class Contract(Base):
    """Договор с сотрудником."""
    
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("contract_templates.id"), nullable=True)
    
    # Основные данные договора
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Финальный текст договора (может генерироваться из шаблона)
    hourly_rate = Column(Integer, nullable=True)  # Почасовая ставка в копейках
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)  # None = бессрочный
    
    # Статус и управление
    status = Column(String(50), nullable=False, default="draft")  # draft, active, suspended, terminated
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Доступ к объектам
    allowed_objects = Column(JSON, nullable=True)  # Список ID объектов, к которым есть доступ
    
    # Поля для управляющих
    is_manager = Column(Boolean, default=False, nullable=False)  # Является ли управляющим
    manager_permissions = Column(JSON, nullable=True)  # Общие права управляющего
    
    # Динамические значения по схеме полей шаблона
    values = Column(JSON, nullable=True)  # {key: value}
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    signed_at = Column(DateTime(timezone=True), nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_contracts")
    employee = relationship("User", foreign_keys=[employee_id], backref="employee_contracts")
    template = relationship("ContractTemplate", back_populates="contracts")
    object_permissions = relationship("ManagerObjectPermission", back_populates="contract")
    
    # Связанные смены (пока без внешних ключей)
    # shifts = relationship("Shift", backref="contract")
    # scheduled_shifts = relationship("ShiftSchedule", backref="contract")


class ContractVersion(Base):
    """Версия договора для отслеживания изменений."""
    
    __tablename__ = "contract_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    version_number = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    changes_description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Отношения
    contract = relationship("Contract", backref="versions")
    creator = relationship("User", backref="created_contract_versions")
