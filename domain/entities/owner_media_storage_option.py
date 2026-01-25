"""Настройки хранилища медиа по владельцу (restruct1 Фаза 1.5)."""

from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey

from .base import Base

CONTEXTS = ("tasks", "cancellations", "incidents", "contracts")
STORAGE_MODES = ("telegram", "storage", "both")


class OwnerMediaStorageOption(Base):
    """Где хранить медиа по контексту: telegram | storage | both."""

    __tablename__ = "owner_media_storage_options"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    context = Column(String(30), nullable=False)  # tasks | cancellations | incidents | contracts
    storage = Column(String(20), nullable=False, default="telegram")  # telegram | storage | both

    __table_args__ = (UniqueConstraint("owner_id", "context", name="uq_owner_media_storage_owner_context"),)

    def __repr__(self) -> str:
        return f"<OwnerMediaStorageOption(owner_id={self.owner_id}, context='{self.context}', storage='{self.storage}')>"
