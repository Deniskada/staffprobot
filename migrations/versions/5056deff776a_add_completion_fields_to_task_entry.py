"""add_completion_fields_to_task_entry

Revision ID: 5056deff776a
Revises: 6fc973252b64
Create Date: 2025-10-27 12:23:46.037964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5056deff776a'
down_revision: Union[str, Sequence[str], None] = '6fc973252b64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поля для хранения результатов выполнения задачи
    op.add_column('task_entries_v2', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('task_entries_v2', sa.Column('completion_notes', sa.Text(), nullable=True))
    op.add_column('task_entries_v2', sa.Column('completion_media', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_entries_v2', 'completion_media')
    op.drop_column('task_entries_v2', 'completion_notes')
    op.drop_column('task_entries_v2', 'completed_at')
