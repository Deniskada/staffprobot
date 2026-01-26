"""add_telegram_file_id_to_cancellation_media

Revision ID: 37f7f5f15c0a
Revises: c3d4e5f6g7h9
Create Date: 2026-01-26 15:54:00.872918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37f7f5f15c0a'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле telegram_file_id для хранения Telegram file_id при storage_mode='both'."""
    op.add_column(
        "shift_cancellation_media",
        sa.Column("telegram_file_id", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    """Удалить поле telegram_file_id."""
    op.drop_column("shift_cancellation_media", "telegram_file_id")
