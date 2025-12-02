"""merge_heads

Revision ID: c4fe42990441
Revises: 20251119a1, 9f7190a2f7c4, b7f8f469c2d1
Create Date: 2025-12-02 11:51:51.631628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4fe42990441'
down_revision: Union[str, Sequence[str], None] = ('20251119a1', '9f7190a2f7c4', 'b7f8f469c2d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
