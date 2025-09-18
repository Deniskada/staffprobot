"""add_auto_closed_to_shift_schedules

Revision ID: dba9f9a350ba
Revises: 2e5b72ddefec
Create Date: 2025-08-29 01:37:12.997481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dba9f9a350ba'
down_revision: Union[str, Sequence[str], None] = 'b348c85b3761'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле auto_closed с значением по умолчанию False
    op.add_column('shift_schedules', sa.Column('auto_closed', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле auto_closed
    op.drop_column('shift_schedules', 'auto_closed')
