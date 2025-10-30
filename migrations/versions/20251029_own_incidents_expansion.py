"""expand incidents, add categories and history

Revision ID: 20251029_incidents_ext
Revises: 
Create Date: 2025-10-29
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251029_incidents_ext'
down_revision = '20251029_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # incidents extra fields
    with op.batch_alter_table('incidents') as batch_op:
        batch_op.add_column(sa.Column('custom_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('custom_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('damage_amount', sa.Numeric(10, 2), nullable=True))
        batch_op.create_index('ix_incidents_custom_number', ['custom_number'], unique=False)
        batch_op.create_index('ix_incidents_custom_date', ['custom_date'], unique=False)

    # incident_categories
    op.create_table(
        'incident_categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_incident_categories_owner', 'incident_categories', ['owner_id'])

    # incident_history
    op.create_table(
        'incident_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('field', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
    )
    op.create_index('ix_incident_history_incident', 'incident_history', ['incident_id'])


def downgrade() -> None:
    op.drop_index('ix_incident_history_incident', table_name='incident_history')
    op.drop_table('incident_history')

    op.drop_index('ix_incident_categories_owner', table_name='incident_categories')
    op.drop_table('incident_categories')

    with op.batch_alter_table('incidents') as batch_op:
        batch_op.drop_index('ix_incidents_custom_date')
        batch_op.drop_index('ix_incidents_custom_number')
        batch_op.drop_column('damage_amount')
        batch_op.drop_column('custom_date')
        batch_op.drop_column('custom_number')


