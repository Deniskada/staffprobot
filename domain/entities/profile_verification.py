"""KYC-верификация профилей (задел под провайдеров)."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ProfileVerification(Base):
    """
    Верификация профиля через провайдера KYC.

    UNIQUE(provider, identity_key) — один реальный субъект = один профиль (KYC-дубли).
    Логика проверки дублей — после rollout MAX.
    """

    __tablename__ = "profile_verifications"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(100), nullable=False, comment="gosuslugi, da-svidetelstvo, ...")
    identity_key = Column(String(255), nullable=False, comment="ИНН, СНИЛС, хэш")
    verified_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "identity_key", name="uq_profile_verif_provider_identity"),
        UniqueConstraint("profile_id", "provider", name="uq_profile_verif_profile_provider"),
    )

    profile = relationship("Profile", backref="verifications")
