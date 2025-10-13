"""merge cancellation system

Revision ID: d906e4471723
Revises: 60fd3b3468b0, add_cancellation_settings
Create Date: 2025-10-13 18:02:18.766283

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd906e4471723'
down_revision: Union[str, Sequence[str], None] = ('60fd3b3468b0', 'add_cancellation_settings')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
