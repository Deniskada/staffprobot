"""merge_develop_notification_migrations

Revision ID: 8d9a120ec66c
Revises: cdbb28b02851, d906e4471723
Create Date: 2025-10-14 11:48:51.794626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d9a120ec66c'
down_revision: Union[str, Sequence[str], None] = ('cdbb28b02851', 'd906e4471723')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
