"""Add SCHEDULED and DELETED to NotificationStatus enum

Revision ID: cdbb28b02851
Revises: 3a9c09063654
Create Date: 2025-10-13 21:54:37.255023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdbb28b02851'
down_revision: Union[str, Sequence[str], None] = '3a9c09063654'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новые значения в ENUM notificationstatus
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'scheduled'")
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'deleted'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL не поддерживает удаление значений из ENUM напрямую
    # Это потребует пересоздания типа, что сложно и опасно
    # Поэтому оставляем downgrade пустым
    # В случае необходимости отката, потребуется ручное вмешательство
    pass
