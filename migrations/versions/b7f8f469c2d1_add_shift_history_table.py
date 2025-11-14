"""add shift_history table

Revision ID: b7f8f469c2d1
Revises: f3b3bb8c9a1f
Create Date: 2025-11-13 21:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7f8f469c2d1'
down_revision: Union[str, Sequence[str], None] = 'f3b3bb8c9a1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create shift_history table for tracking shift lifecycle operations."""
    op.create_table(
        'shift_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=True),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False, server_default='web'),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=True),
        sa.Column('old_status', sa.String(length=32), nullable=True),
        sa.Column('new_status', sa.String(length=32), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name='fk_shift_history_actor', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['schedule_id'], ['shift_schedules.id'], name='fk_shift_history_schedule', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], name='fk_shift_history_shift', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shift_history_shift_id', 'shift_history', ['shift_id'])
    op.create_index('ix_shift_history_schedule_id', 'shift_history', ['schedule_id'])
    op.create_index('ix_shift_history_actor_id', 'shift_history', ['actor_id'])
    op.create_index('ix_shift_history_operation', 'shift_history', ['operation'])
    op.create_index('ix_shift_history_created_at', 'shift_history', ['created_at'])


def downgrade() -> None:
    """Drop shift_history table."""
    op.drop_index('ix_shift_history_created_at', table_name='shift_history')
    op.drop_index('ix_shift_history_operation', table_name='shift_history')
    op.drop_index('ix_shift_history_actor_id', table_name='shift_history')
    op.drop_index('ix_shift_history_schedule_id', table_name='shift_history')
    op.drop_index('ix_shift_history_shift_id', table_name='shift_history')
    op.drop_table('shift_history')

