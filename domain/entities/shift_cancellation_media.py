"""Медиа-файлы отмены смены (restruct1 Фаза 1.4)."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ShiftCancellationMedia(Base):
    """Медиа-файлы, приложенные к отмене смены (справки, подтверждения)."""

    __tablename__ = "shift_cancellation_media"

    id = Column(Integer, primary_key=True, index=True)
    cancellation_id = Column(
        Integer,
        ForeignKey("shift_cancellations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_type = Column(String(20), nullable=False)  # 'photo' | 'video' | 'document'
    storage_key = Column(String(500), nullable=False)  # key в хранилище (S3 path / telegram file_id)
    telegram_file_id = Column(String(200), nullable=True)  # Telegram file_id (если медиа есть и в Telegram)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cancellation = relationship(
        "ShiftCancellation",
        backref="media_files",
        foreign_keys=[cancellation_id],
    )

    def __repr__(self) -> str:
        return f"<ShiftCancellationMedia(id={self.id}, cancellation_id={self.cancellation_id}, file_type='{self.file_type}')>"
