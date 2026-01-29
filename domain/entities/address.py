"""Модель адреса для повторного использования в профилях и других сущностях."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Address(Base):
    """Нормализованный адрес из внутренней базы адресов."""

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)

    # Пользователь, добавивший адрес (для персональных подборок)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Внутренний ID пользователя, создавшего адрес",
    )

    country = Column(String(100), nullable=False, default="Россия")
    region = Column(String(255), nullable=True)
    city = Column(String(255), nullable=False)
    street = Column(String(255), nullable=True)
    house = Column(String(50), nullable=True)
    building = Column(String(50), nullable=True)
    apartment = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Дополнительное поле для человекочитаемого полного адреса/подсказки
    full_address = Column(String(1000), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи будут определяться на стороне профилей/объектов (FK на address_id)

    def __repr__(self) -> str:
        parts = [self.country, self.region, self.city, self.street, self.house]
        human = ", ".join([p for p in parts if p])
        return f"<Address(id={self.id}, {human})>"

