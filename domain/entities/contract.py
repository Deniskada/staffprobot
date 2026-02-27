"""Модели для системы договоров."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Numeric, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional


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
    contract_type_id = Column(Integer, ForeignKey("contract_types.id", ondelete="SET NULL"), nullable=True, index=True)
    constructor_flow_id = Column(Integer, ForeignKey("constructor_flows.id", ondelete="SET NULL"), nullable=True, index=True)
    constructor_values = Column(JSON, nullable=True)  # step_choices из мастера (customer_profile_id и др.)

    # Отношения
    creator = relationship("User", backref="created_templates")
    contracts = relationship("Contract", back_populates="template")
    contract_type = relationship("ContractType", backref="templates")
    constructor_flow = relationship("ConstructorFlow", backref="templates")


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
    hourly_rate = Column(Numeric(10, 2), nullable=True)  # Почасовая ставка в рублях
    use_contract_rate = Column(Boolean, default=False, nullable=False, index=True)  # Приоритет ставки договора
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    use_contract_payment_system = Column(Boolean, default=False, nullable=False, index=True)  # Приоритет системы оплаты договора
    payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    inherit_payment_schedule = Column(Boolean, default=True, nullable=False)  # Наследовать график выплат от подразделения
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
    
    # Поля для увольнения и финального расчёта
    termination_date = Column(Date, nullable=True)  # Дата увольнения
    settlement_policy = Column(String(32), nullable=False, default="schedule")  # 'schedule' | 'termination_date'
    
    # Метаданные ПЭП (простой электронной подписи)
    pep_metadata = Column(JSON, nullable=True, comment="Метаданные ПЭП: channel, otp_hash, esia_oid, signed_ip")
    
    # Отношения
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_contracts")
    employee = relationship("User", foreign_keys=[employee_id], backref="employee_contracts")
    template = relationship("ContractTemplate", back_populates="contracts")
    payment_system = relationship("PaymentSystem", backref="contracts")
    payment_schedule = relationship("PaymentSchedule", foreign_keys=[payment_schedule_id], backref="assigned_contracts")
    object_permissions = relationship("ManagerObjectPermission", back_populates="contract")
    
    # Связанные смены (пока без внешних ключей)
    # shifts = relationship("Shift", backref="contract")
    # scheduled_shifts = relationship("ShiftSchedule", backref="contract")
    
    def get_effective_hourly_rate(
        self, 
        timeslot_rate: Optional[float] = None,
        object_rate: Optional[float] = None
    ) -> Optional[float]:
        """
        Определить эффективную почасовую ставку с учетом приоритетов.
        
        Приоритет:
        1. contract.hourly_rate (ТОЛЬКО если use_contract_rate=True)
        2. timeslot_rate (если указан)
        3. object_rate (fallback)
        
        Args:
            timeslot_rate: Ставка тайм-слота (если смена запланированная)
            object_rate: Ставка объекта (fallback)
            
        Returns:
            Эффективная ставка в рублях или None
        """
        # Приоритет 1: Ставка договора (ТОЛЬКО если флаг включен)
        if self.use_contract_rate and self.hourly_rate is not None:
            return float(self.hourly_rate)
        
        # Приоритет 2: Ставка тайм-слота
        if timeslot_rate is not None:
            return float(timeslot_rate)
        
        # Приоритет 3: Ставка объекта
        if object_rate is not None:
            return float(object_rate)
        
        # Если ничего не найдено - вернуть None
        return None
    
    def get_effective_payment_system_id(
        self,
        object_payment_system_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Определить эффективную систему оплаты с учетом приоритетов.
        
        Приоритет:
        1. contract.payment_system_id (ТОЛЬКО если use_contract_payment_system=True)
        2. object_payment_system_id (с учетом наследования от подразделения)
        
        Args:
            object_payment_system_id: Система оплаты объекта (с наследованием)
            
        Returns:
            ID системы оплаты или None
        """
        # Приоритет 1: Система оплаты договора (ТОЛЬКО если флаг включен)
        if self.use_contract_payment_system and self.payment_system_id is not None:
            return self.payment_system_id
        
        # Приоритет 2: Система оплаты объекта (с учетом наследования)
        return object_payment_system_id


class ContractVersion(Base):
    """Версия договора для отслеживания изменений."""
    
    __tablename__ = "contract_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    version_number = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    changes_description = Column(Text, nullable=True)
    file_key = Column(String(500), nullable=True, comment="Ключ подписанного PDF в S3")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Отношения
    contract = relationship("Contract", backref="versions")
    creator = relationship("User", backref="created_contract_versions")
