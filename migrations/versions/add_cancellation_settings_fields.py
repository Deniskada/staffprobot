"""add cancellation settings fields

Revision ID: add_cancellation_settings
Revises: add_shift_cancellations
Create Date: 2025-10-13 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_cancellation_settings'
down_revision = 'add_shift_cancellations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавление полей настроек отмены в таблицу objects
    op.add_column('objects', sa.Column('inherit_cancellation_settings', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('objects', sa.Column('cancellation_short_notice_hours', sa.Integer(), nullable=True))
    op.add_column('objects', sa.Column('cancellation_short_notice_fine', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('objects', sa.Column('cancellation_invalid_reason_fine', sa.Numeric(precision=10, scale=2), nullable=True))
    
    # Создание индекса для inherit_cancellation_settings
    op.create_index('ix_objects_inherit_cancellation_settings', 'objects', ['inherit_cancellation_settings'])
    
    # Добавление полей настроек отмены в таблицу org_structure_units
    op.add_column('org_structure_units', sa.Column('inherit_cancellation_settings', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('org_structure_units', sa.Column('cancellation_short_notice_hours', sa.Integer(), nullable=True))
    op.add_column('org_structure_units', sa.Column('cancellation_short_notice_fine', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('org_structure_units', sa.Column('cancellation_invalid_reason_fine', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    # Удаление полей из org_structure_units
    op.drop_column('org_structure_units', 'cancellation_invalid_reason_fine')
    op.drop_column('org_structure_units', 'cancellation_short_notice_fine')
    op.drop_column('org_structure_units', 'cancellation_short_notice_hours')
    op.drop_column('org_structure_units', 'inherit_cancellation_settings')
    
    # Удаление индекса и полей из objects
    op.drop_index('ix_objects_inherit_cancellation_settings', table_name='objects')
    op.drop_column('objects', 'cancellation_invalid_reason_fine')
    op.drop_column('objects', 'cancellation_short_notice_fine')
    op.drop_column('objects', 'cancellation_short_notice_hours')
    op.drop_column('objects', 'inherit_cancellation_settings')

