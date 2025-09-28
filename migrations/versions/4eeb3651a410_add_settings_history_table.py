"""add_settings_history_table

Revision ID: 4eeb3651a410
Revises: e90f9e042f36
Create Date: 2025-09-28 15:27:22.834503

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4eeb3651a410'
down_revision: Union[str, Sequence[str], None] = 'e90f9e042f36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('settings_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('setting_key', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.String(length=100), nullable=True),
        sa.Column('change_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_history_id'), 'settings_history', ['id'], unique=False)
    op.create_index(op.f('ix_settings_history_setting_key'), 'settings_history', ['setting_key'], unique=False)
    op.create_index(op.f('ix_settings_history_created_at'), 'settings_history', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_settings_history_created_at'), table_name='settings_history')
    op.drop_index(op.f('ix_settings_history_setting_key'), table_name='settings_history')
    op.drop_index(op.f('ix_settings_history_id'), table_name='settings_history')
    op.drop_table('settings_history')
