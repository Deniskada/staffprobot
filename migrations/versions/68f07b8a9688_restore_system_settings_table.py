"""restore_system_settings_table

Revision ID: 68f07b8a9688
Revises: c887be040290
Create Date: 2025-11-01 00:06:43.884457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68f07b8a9688'
down_revision: Union[str, Sequence[str], None] = 'c887be040290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Восстанавливаем таблицу system_settings, которая была удалена в миграции a266c36de460
    op.create_table('system_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)
    op.create_unique_constraint('system_settings_key_key', 'system_settings', ['key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('system_settings_key_key', 'system_settings', type_='unique')
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_index(op.f('ix_system_settings_id'), table_name='system_settings')
    op.drop_table('system_settings')
