"""add_object_notification_types_to_enum

Revision ID: 809625543f59
Revises: d26963b1a623
Create Date: 2025-10-31 10:50:20.481220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '809625543f59'
down_revision: Union[str, Sequence[str], None] = 'd26963b1a623'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить новые типы уведомлений для объектов в enum notificationtype."""
    # Добавляем новые значения в enum
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'object_opened'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'object_closed'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'object_late_opening'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'object_no_shifts_today'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'object_early_closing'")


def downgrade() -> None:
    """Downgrade schema."""
    # ВНИМАНИЕ: PostgreSQL не поддерживает удаление значений из enum
    # Downgrade невозможен без пересоздания типа
    pass
