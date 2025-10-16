"""remove_shift_tasks_jsonb_from_timeslots

Revision ID: 47854ebf33dc
Revises: 8d9a120ec66c
Create Date: 2025-10-16 12:12:33.630890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47854ebf33dc'
down_revision: Union[str, Sequence[str], None] = '8d9a120ec66c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Удаляет JSONB поле shift_tasks из таблицы time_slots.
    
    Задачи тайм-слотов теперь хранятся только в таблице timeslot_task_templates.
    """
    op.drop_column('time_slots', 'shift_tasks')


def downgrade() -> None:
    """
    Восстанавливает JSONB поле shift_tasks в таблице time_slots.
    
    Внимание: данные не восстанавливаются!
    """
    op.add_column('time_slots', sa.Column('shift_tasks', sa.dialects.postgresql.JSONB(), nullable=True))
