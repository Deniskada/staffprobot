"""add_user_roles_enum

Revision ID: 3fe3022e79cf
Revises: 90f267d839c9
Create Date: 2025-09-06 14:59:26.982887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fe3022e79cf'
down_revision: Union[str, Sequence[str], None] = '90f267d839c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Эта миграция не требует изменений в схеме
    # Роли уже определены в модели User
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Эта миграция не требует изменений в схеме
    pass
