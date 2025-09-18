"""add_time_slots_table

Revision ID: 20250828_add_time_slots_table
Revises: 97844e8c2d47
Create Date: 2025-08-28 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250828_add_time_slots_table'
down_revision: Union[str, Sequence[str], None] = '97844e8c2d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create time_slots table to support time-slot based scheduling."""
    op.create_table(
        'time_slots',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=False, index=True),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('hourly_rate', sa.Numeric(10, 2), nullable=True),
        sa.Column('max_employees', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('is_additional', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['object_id'], ['objects.id']),
    )
    # Индексы создаются автоматически для колонок c index=True при autogenerate


def downgrade() -> None:
    op.drop_table('time_slots')


