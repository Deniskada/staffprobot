"""create_contract_terminations_table

Revision ID: f7b35e4d704c
Revises: 7ea5d1851f43
Create Date: 2025-10-19 20:54:37.382078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b35e4d704c'
down_revision: Union[str, Sequence[str], None] = '7ea5d1851f43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'contract_terminations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('terminated_by_id', sa.Integer(), nullable=False),
        sa.Column('terminated_by_type', sa.String(length=32), nullable=False),  # 'owner', 'manager', 'system'
        sa.Column('reason_category', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('termination_date', sa.Date(), nullable=True),
        sa.Column('settlement_policy', sa.String(length=32), nullable=False),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_contract_terminations_contract_id', 'contract_terminations', ['contract_id'])
    op.create_index('ix_contract_terminations_employee_id', 'contract_terminations', ['employee_id'])
    op.create_index('ix_contract_terminations_owner_id', 'contract_terminations', ['owner_id'])
    op.create_index('ix_contract_terminations_terminated_at', 'contract_terminations', ['terminated_at'])
    op.create_index('ix_contract_terminations_reason_category', 'contract_terminations', ['reason_category'])
    
    op.create_foreign_key(
        'fk_contract_terminations_contract_id',
        'contract_terminations', 'contracts',
        ['contract_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_contract_terminations_employee_id',
        'contract_terminations', 'users',
        ['employee_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_contract_terminations_owner_id',
        'contract_terminations', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_contract_terminations_terminated_by_id',
        'contract_terminations', 'users',
        ['terminated_by_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_contract_terminations_terminated_by_id', 'contract_terminations', type_='foreignkey')
    op.drop_constraint('fk_contract_terminations_owner_id', 'contract_terminations', type_='foreignkey')
    op.drop_constraint('fk_contract_terminations_employee_id', 'contract_terminations', type_='foreignkey')
    op.drop_constraint('fk_contract_terminations_contract_id', 'contract_terminations', type_='foreignkey')
    
    op.drop_index('ix_contract_terminations_reason_category', table_name='contract_terminations')
    op.drop_index('ix_contract_terminations_terminated_at', table_name='contract_terminations')
    op.drop_index('ix_contract_terminations_owner_id', table_name='contract_terminations')
    op.drop_index('ix_contract_terminations_employee_id', table_name='contract_terminations')
    op.drop_index('ix_contract_terminations_contract_id', table_name='contract_terminations')
    
    op.drop_table('contract_terminations')
