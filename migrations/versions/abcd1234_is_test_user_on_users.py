"""Add is_test_user column to users

Revision ID: abcd1234
Revises: 067655939741
Create Date: 2025-10-08 02:41:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abcd1234'
down_revision: Union[str, Sequence[str], None] = '067655939741'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    try:
        op.add_column('users', sa.Column('is_test_user', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    except Exception:
        # Столбец уже существует (dev hotfix)
        pass


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_column('users', 'is_test_user')
    except Exception:
        pass


