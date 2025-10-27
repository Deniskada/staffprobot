"""create_shift_tasks_table

Revision ID: e73e979cde11
Revises: 483be5c7fa46
Create Date: 2025-10-27 13:40:09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e73e979cde11'
down_revision: Union[str, Sequence[str], None] = '483be5c7fa46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'shift_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('task_text', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_media', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deduction_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('media_refs', postgresql.JSON(), nullable=True),
        sa.Column('correction_ref', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Индексы
    op.create_index('ix_shift_tasks_shift_id', 'shift_tasks', ['shift_id'])
    op.create_index('ix_shift_tasks_source', 'shift_tasks', ['source'])
    op.create_index('ix_shift_tasks_is_mandatory', 'shift_tasks', ['is_mandatory'])
    op.create_index('ix_shift_tasks_is_completed', 'shift_tasks', ['is_completed'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_shift_tasks_is_completed', 'shift_tasks')
    op.drop_index('ix_shift_tasks_is_mandatory', 'shift_tasks')
    op.drop_index('ix_shift_tasks_source', 'shift_tasks')
    op.drop_index('ix_shift_tasks_shift_id', 'shift_tasks')
    op.drop_table('shift_tasks')
