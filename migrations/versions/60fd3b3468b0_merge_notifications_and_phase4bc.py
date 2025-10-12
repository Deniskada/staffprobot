"""merge_notifications_and_phase4bc

Revision ID: 60fd3b3468b0
Revises: 21bdf8e9a3c7, 3bcf125fefbd
Create Date: 2025-10-12 12:20:31.008473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60fd3b3468b0'
down_revision: Union[str, Sequence[str], None] = ('21bdf8e9a3c7', '3bcf125fefbd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
