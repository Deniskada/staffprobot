"""Модель документов профиля (сканы паспорта, ИНН, СНИЛС и пр.)."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ProfileDocument(Base):
    """Скан/фото документа, привязанный к профилю пользователя."""

    __tablename__ = "profile_documents"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="passport_main | passport_registration | inn_scan | snils_scan",
    )
    file_key = Column(String(500), nullable=False, comment="Ключ файла в S3")
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("Profile", backref="documents")
