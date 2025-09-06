"""merge_heads

Revision ID: 0157a54a5e7e
Revises: b348c85b3761, dba9f9a350ba
Create Date: 2025-09-06 09:21:33.970708

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0157a54a5e7e'
down_revision: Union[str, Sequence[str], None] = ('b348c85b3761', 'dba9f9a350ba')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
