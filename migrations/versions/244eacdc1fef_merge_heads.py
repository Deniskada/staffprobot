"""merge_heads

Revision ID: 244eacdc1fef
Revises: 20251023_001, 20251027_001
Create Date: 2025-10-27 11:08:41.294016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '244eacdc1fef'
down_revision: Union[str, Sequence[str], None] = ('20251023_001', '20251027_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
