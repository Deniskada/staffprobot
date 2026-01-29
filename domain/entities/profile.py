"""Модели профилей пользователей (ФЛ, ИП, ЮЛ) и KYC‑статус."""

from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ProfileType(str, Enum):
    """Тип профиля пользователя."""

    INDIVIDUAL = "individual"  # Физическое лицо
    LEGAL = "legal"  # Юридическое лицо
    SOLE_PROPRIETOR = "sole_proprietor"  # Индивидуальный предприниматель


class KycStatus(str, Enum):
    """Статус KYC‑верификации профиля."""

    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class Profile(Base):
    """
    Базовый профиль пользователя.

    Один пользователь может иметь несколько профилей разных типов.
    Типоспецифичные данные хранятся в связанных таблицах.
    """

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Внутренний ID пользователя (users.id)",
    )

    profile_type = Column(
        String(32),
        nullable=False,
        comment="Тип профиля: individual / legal / sole_proprietor",
    )

    display_name = Column(
        String(255),
        nullable=False,
        comment="Отображаемое имя профиля (например: Иванов И.И., ООО Ромашка)",
    )

    is_default = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Профиль по умолчанию для пользователя",
    )

    is_archived = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Архивный профиль (скрыт из основного списка)",
    )

    # KYC‑атрибуты
    kyc_status = Column(
        String(32),
        nullable=False,
        default=KycStatus.UNVERIFIED.value,
        comment="Статус KYC‑верификации профиля",
    )
    kyc_provider = Column(
        String(100),
        nullable=True,
        comment="Код провайдера KYC (например, gosuslugi)",
    )
    kyc_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время успешной KYC‑верификации",
    )
    kyc_metadata = Column(
        JSON,
        nullable=True,
        comment="Служебные данные KYC‑проверки (payload провайдера)",
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи
    user = relationship("User", backref="profiles")
    individual_profile = relationship(
        "IndividualProfile",
        back_populates="profile",
        uselist=False,
    )
    legal_profile = relationship(
        "LegalProfile",
        back_populates="profile",
        uselist=False,
    )
    sole_proprietor_profile = relationship(
        "SoleProprietorProfile",
        back_populates="profile",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, user_id={self.user_id}, type={self.profile_type}, kyc={self.kyc_status})>"

    def is_verified(self) -> bool:
        """Профиль прошёл KYC‑верификацию."""
        return self.kyc_status == KycStatus.VERIFIED.value


class ContactInfoMixin:
    """Общий набор полей контактной информации."""

    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    max_contact = Column(String(255), nullable=True, comment="Контакт MAX")


class BankDetailsMixin:
    """Общий набор полей банковских реквизитов."""

    account_number = Column(String(32), nullable=True, comment="Расчетный счет")
    correspondent_account = Column(String(32), nullable=True, comment="Корреспондентский счет")
    bank_name = Column(String(255), nullable=True, comment="Наименование банка")
    bik = Column(String(20), nullable=True, comment="БИК")


class IndividualProfile(Base, ContactInfoMixin, BankDetailsMixin):
    """Профиль физического лица."""

    __tablename__ = "individual_profiles"

    id = Column(Integer, primary_key=True)
    profile_id = Column(
        Integer,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Гражданство
    citizenship = Column(
        String(32),
        nullable=False,
        comment="rf / foreign / stateless",
    )

    # Личные данные
    last_name = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    middle_name = Column(String(255), nullable=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    gender = Column(String(16), nullable=True, comment="male / female")
    is_self_employed = Column(Boolean, nullable=False, default=False)

    # Паспорт
    passport_series = Column(String(10), nullable=True)
    passport_number = Column(String(20), nullable=True)
    passport_issued_at = Column(DateTime(timezone=True), nullable=True)
    passport_issued_by = Column(String(500), nullable=True)
    passport_department_code = Column(String(20), nullable=True)
    registration_address_id = Column(
        Integer,
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Адрес регистрации (FK на addresses.id)",
    )

    # Регистрационные данные
    snils = Column(String(20), nullable=True)
    inn = Column(String(20), nullable=True)

    # Дополнительный адрес проживания (может совпадать с регистрацией)
    residence_address_id = Column(
        Integer,
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Адрес проживания (FK на addresses.id)",
    )

    profile = relationship("Profile", back_populates="individual_profile")
    registration_address = relationship(
        "Address",
        foreign_keys=[registration_address_id],
    )
    residence_address = relationship(
        "Address",
        foreign_keys=[residence_address_id],
    )


class LegalProfile(Base, ContactInfoMixin, BankDetailsMixin):
    """Профиль юридического лица."""

    __tablename__ = "legal_profiles"

    id = Column(Integer, primary_key=True)
    profile_id = Column(
        Integer,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    full_name = Column(String(500), nullable=False)
    ogrn = Column(String(20), nullable=True)
    ogrn_assigned_at = Column(DateTime(timezone=True), nullable=True)
    inn = Column(String(20), nullable=True)
    okpo = Column(String(20), nullable=True)

    # Адрес регистрации (по ЕГРЮЛ)
    registration_address_id = Column(
        Integer,
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Адрес регистрации юридического лица (ЕГРЮЛ)",
    )

    # Адрес фактического нахождения в РФ
    address_rf_id = Column(
        Integer,
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Адрес в РФ (фактический)",
    )

    # Представитель (ФЛ‑профиль)
    representative_profile_id = Column(
        Integer,
        ForeignKey("individual_profiles.id", ondelete="SET NULL"),
        nullable=True,
        comment="Профиль представителя (ФЛ)",
    )
    representative_basis = Column(
        String(500),
        nullable=True,
        comment="Основание полномочий (например, Устав)",
    )
    representative_position = Column(String(255), nullable=True)

    profile = relationship("Profile", back_populates="legal_profile")
    registration_address = relationship(
        "Address",
        foreign_keys=[registration_address_id],
    )
    address_rf = relationship(
        "Address",
        foreign_keys=[address_rf_id],
    )
    representative_profile = relationship("IndividualProfile")


class SoleProprietorProfile(Base, ContactInfoMixin, BankDetailsMixin):
    """Профиль индивидуального предпринимателя."""

    __tablename__ = "sole_proprietor_profiles"

    id = Column(Integer, primary_key=True)
    profile_id = Column(
        Integer,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Личные данные
    last_name = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    middle_name = Column(String(255), nullable=True)
    gender = Column(String(16), nullable=True, comment="male / female")

    # Регистрационные данные
    ogrnip = Column(String(20), nullable=True)
    inn = Column(String(20), nullable=True)
    okpo = Column(String(20), nullable=True)

    # Адрес проживания
    residence_address_id = Column(
        Integer,
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Адрес места жительства",
    )

    profile = relationship("Profile", back_populates="sole_proprietor_profile")
    residence_address = relationship("Address")

