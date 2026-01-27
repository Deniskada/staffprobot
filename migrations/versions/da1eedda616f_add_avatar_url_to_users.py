"""add_avatar_url_to_users

Revision ID: da1eedda616f
Revises: 37f7f5f15c0a
Create Date: 2026-01-26 20:51:56.705645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da1eedda616f'
down_revision: Union[str, Sequence[str], None] = '37f7f5f15c0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле avatar_url для хранения URL фото профиля."""
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Удалить поле avatar_url."""
    op.drop_column("users", "avatar_url")
