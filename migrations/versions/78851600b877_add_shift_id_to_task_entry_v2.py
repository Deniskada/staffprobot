"""add_shift_id_to_task_entry_v2

Revision ID: 78851600b877
Revises: e73e979cde11
Create Date: 2025-10-27 17:05:38.559330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78851600b877'
down_revision: Union[str, Sequence[str], None] = 'e73e979cde11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем столбец shift_id
    op.add_column('task_entries_v2', sa.Column('shift_id', sa.Integer(), nullable=True))
    
    # Создаём foreign key на shifts
    op.create_foreign_key(
        'fk_task_entries_v2_shift_id',
        'task_entries_v2', 'shifts',
        ['shift_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Создаём индекс для быстрого поиска
    op.create_index('ix_task_entries_v2_shift_id', 'task_entries_v2', ['shift_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_task_entries_v2_shift_id', 'task_entries_v2')
    op.drop_constraint('fk_task_entries_v2_shift_id', 'task_entries_v2', type_='foreignkey')
    op.drop_column('task_entries_v2', 'shift_id')
