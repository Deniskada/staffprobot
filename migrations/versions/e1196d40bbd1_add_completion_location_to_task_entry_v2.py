"""add_completion_location_to_task_entry_v2

Revision ID: e1196d40bbd1
Revises: c6b88a3de81e
Create Date: 2025-11-04 22:28:15.415846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e1196d40bbd1'
down_revision: Union[str, Sequence[str], None] = 'c6b88a3de81e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле completion_location в task_entries_v2."""
    op.add_column('task_entries_v2', sa.Column('completion_location', sa.Text(), nullable=True))


def downgrade() -> None:
    """Удалить поле completion_location из task_entries_v2."""
    op.drop_column('task_entries_v2', 'completion_location')
