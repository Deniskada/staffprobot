"""add_object_state_management

Revision ID: 3bcf125fefbd
Revises: 96bcb588d0c8
Create Date: 2025-10-11 17:53:46.220488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3bcf125fefbd'
down_revision: Union[str, Sequence[str], None] = '96bcb588d0c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Создать таблицу object_openings
    op.create_table(
        'object_openings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=False),
        sa.Column('opened_by', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('open_coordinates', sa.String(100), nullable=True),
        sa.Column('closed_by', sa.Integer(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_coordinates', sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(['object_id'], ['objects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opened_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_object_openings_id', 'object_openings', ['id'])
    op.create_index('ix_object_openings_object_id', 'object_openings', ['object_id'])
    op.create_index('ix_object_openings_closed_at', 'object_openings', ['closed_at'])
    op.create_index('ix_object_openings_active', 'object_openings', ['object_id', 'closed_at'])
    op.create_index('ix_object_openings_opened_at', 'object_openings', ['opened_at'])
    
    # 2. Добавить поля в time_slots
    op.add_column('time_slots', sa.Column('penalize_late_start', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('time_slots', sa.Column('ignore_object_tasks', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('time_slots', sa.Column('shift_tasks', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # 3. Добавить поля в shifts
    op.add_column('shifts', sa.Column('planned_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shifts', sa.Column('actual_start', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_shifts_planned_start', 'shifts', ['planned_start'])
    op.create_index('ix_shifts_actual_start', 'shifts', ['actual_start'])


def downgrade() -> None:
    """Downgrade schema."""
    # 3. Удалить поля из shifts
    op.drop_index('ix_shifts_actual_start', table_name='shifts')
    op.drop_index('ix_shifts_planned_start', table_name='shifts')
    op.drop_column('shifts', 'actual_start')
    op.drop_column('shifts', 'planned_start')
    
    # 2. Удалить поля из time_slots
    op.drop_column('time_slots', 'shift_tasks')
    op.drop_column('time_slots', 'ignore_object_tasks')
    op.drop_column('time_slots', 'penalize_late_start')
    
    # 1. Удалить таблицу object_openings
    op.drop_index('ix_object_openings_opened_at', table_name='object_openings')
    op.drop_index('ix_object_openings_active', table_name='object_openings')
    op.drop_index('ix_object_openings_closed_at', table_name='object_openings')
    op.drop_index('ix_object_openings_object_id', table_name='object_openings')
    op.drop_index('ix_object_openings_id', table_name='object_openings')
    op.drop_table('object_openings')
