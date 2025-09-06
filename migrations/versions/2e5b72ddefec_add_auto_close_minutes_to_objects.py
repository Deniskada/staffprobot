"""add_auto_close_minutes_to_objects

Revision ID: 2e5b72ddefec
Revises: 20250828_add_time_slots_table
Create Date: 2025-08-29 01:34:53.997481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e5b72ddefec'
down_revision: Union[str, Sequence[str], None] = '97844e8c2d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле auto_close_minutes с значением по умолчанию 60
    op.add_column('objects', sa.Column('auto_close_minutes', sa.Integer(), nullable=False, server_default='60'))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле auto_close_minutes
    op.drop_column('objects', 'auto_close_minutes')
