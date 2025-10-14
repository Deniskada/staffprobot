"""add shift cancellations table

Revision ID: add_shift_cancellations
Revises: fix_user_role_defaults
Create Date: 2025-10-13 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_shift_cancellations'
down_revision = 'fix_user_role_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создание таблицы shift_cancellations
    op.create_table(
        'shift_cancellations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_schedule_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=False),
        sa.Column('cancelled_by_id', sa.Integer(), nullable=False),
        sa.Column('cancelled_by_type', sa.String(length=20), nullable=False),
        sa.Column('cancellation_reason', sa.String(length=50), nullable=False),
        sa.Column('reason_notes', sa.Text(), nullable=True),
        sa.Column('hours_before_shift', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('document_description', sa.Text(), nullable=True),
        sa.Column('document_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_by_id', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fine_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('fine_reason', sa.String(length=50), nullable=True),
        sa.Column('fine_applied', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('payroll_adjustment_id', sa.Integer(), nullable=True),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['cancelled_by_id'], ['users.id'], name='fk_shift_cancellations_cancelled_by'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name='fk_shift_cancellations_contract'),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id'], name='fk_shift_cancellations_employee'),
        sa.ForeignKeyConstraint(['object_id'], ['objects.id'], name='fk_shift_cancellations_object'),
        # sa.ForeignKeyConstraint(['payroll_adjustment_id'], ['payroll_adjustments.id'], name='fk_shift_cancellations_payroll_adj'),  # Таблица payroll_adjustments пока не создана
        sa.ForeignKeyConstraint(['shift_schedule_id'], ['shift_schedules.id'], name='fk_shift_cancellations_shift_schedule', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], name='fk_shift_cancellations_verified_by'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание индексов
    op.create_index('ix_shift_cancellations_shift_schedule_id', 'shift_cancellations', ['shift_schedule_id'])
    op.create_index('ix_shift_cancellations_employee_id', 'shift_cancellations', ['employee_id'])
    op.create_index('ix_shift_cancellations_cancelled_by_type', 'shift_cancellations', ['cancelled_by_type'])
    op.create_index('ix_shift_cancellations_cancellation_reason', 'shift_cancellations', ['cancellation_reason'])
    op.create_index('ix_shift_cancellations_fine_applied', 'shift_cancellations', ['fine_applied'])
    op.create_index('ix_shift_cancellations_created_at', 'shift_cancellations', ['created_at'])
    # op.create_index('ix_shift_cancellations_payroll_adjustment_id', 'shift_cancellations', ['payroll_adjustment_id'])  # Пока не создана таблица


def downgrade() -> None:
    # Удаление индексов
    # op.drop_index('ix_shift_cancellations_payroll_adjustment_id', table_name='shift_cancellations')  # Пока не создана
    op.drop_index('ix_shift_cancellations_created_at', table_name='shift_cancellations')
    op.drop_index('ix_shift_cancellations_fine_applied', table_name='shift_cancellations')
    op.drop_index('ix_shift_cancellations_cancellation_reason', table_name='shift_cancellations')
    op.drop_index('ix_shift_cancellations_cancelled_by_type', table_name='shift_cancellations')
    op.drop_index('ix_shift_cancellations_employee_id', table_name='shift_cancellations')
    op.drop_index('ix_shift_cancellations_shift_schedule_id', table_name='shift_cancellations')
    
    # Удаление таблицы
    op.drop_table('shift_cancellations')

