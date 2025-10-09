"""create_payroll_tables

Создание таблиц для системы учета начислений и выплат.

Revision ID: 0e923f2961bb
Revises: 31098b7aa38c
Create Date: 2025-10-09 15:08:54.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0e923f2961bb'
down_revision: Union[str, Sequence[str], None] = '31098b7aa38c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблиц payroll."""
    
    # === 1. PAYROLL_ENTRIES ===
    
    op.create_table(
        'payroll_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('hours_worked', sa.Numeric(10, 2), nullable=False),
        sa.Column('hourly_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('gross_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_deductions', sa.Numeric(10, 2), server_default='0', nullable=False),
        sa.Column('total_bonuses', sa.Numeric(10, 2), server_default='0', nullable=False),
        sa.Column('net_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('calculation_details', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['object_id'], ['objects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для payroll_entries
    op.create_index('idx_payroll_entries_id', 'payroll_entries', ['id'])
    op.create_index('idx_payroll_entries_employee_id', 'payroll_entries', ['employee_id'])
    op.create_index('idx_payroll_entries_contract_id', 'payroll_entries', ['contract_id'])
    op.create_index('idx_payroll_entries_object_id', 'payroll_entries', ['object_id'])
    op.create_index('idx_payroll_entries_period_start', 'payroll_entries', ['period_start'])
    op.create_index('idx_payroll_entries_period_end', 'payroll_entries', ['period_end'])
    op.create_index('idx_payroll_entries_calculation_details', 'payroll_entries', ['calculation_details'], postgresql_using='gin')
    
    # Комментарии
    op.execute("COMMENT ON TABLE payroll_entries IS 'Записи начислений зарплаты'")
    op.execute("COMMENT ON COLUMN payroll_entries.calculation_details IS 'Детали расчета в JSON (смены, корректировки)'")
    
    # === 2. PAYROLL_DEDUCTIONS ===
    
    op.create_table(
        'payroll_deductions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payroll_entry_id', sa.Integer(), nullable=False),
        sa.Column('deduction_type', sa.String(50), nullable=False),
        sa.Column('is_automatic', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['payroll_entry_id'], ['payroll_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для payroll_deductions
    op.create_index('idx_payroll_deductions_id', 'payroll_deductions', ['id'])
    op.create_index('idx_payroll_deductions_payroll_entry_id', 'payroll_deductions', ['payroll_entry_id'])
    op.create_index('idx_payroll_deductions_deduction_type', 'payroll_deductions', ['deduction_type'])
    op.create_index('idx_payroll_deductions_is_automatic', 'payroll_deductions', ['is_automatic'])
    op.create_index('idx_payroll_deductions_details', 'payroll_deductions', ['details'], postgresql_using='gin')
    
    # Комментарии
    op.execute("COMMENT ON TABLE payroll_deductions IS 'Удержания из зарплаты'")
    op.execute("COMMENT ON COLUMN payroll_deductions.deduction_type IS 'Тип: late_start, missed_task, manual, tax, other'")
    op.execute("COMMENT ON COLUMN payroll_deductions.details IS 'Дополнительные данные в JSON (shift_id, task_id и т.д.)'")
    
    # === 3. PAYROLL_BONUSES ===
    
    op.create_table(
        'payroll_bonuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payroll_entry_id', sa.Integer(), nullable=False),
        sa.Column('bonus_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['payroll_entry_id'], ['payroll_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для payroll_bonuses
    op.create_index('idx_payroll_bonuses_id', 'payroll_bonuses', ['id'])
    op.create_index('idx_payroll_bonuses_payroll_entry_id', 'payroll_bonuses', ['payroll_entry_id'])
    op.create_index('idx_payroll_bonuses_bonus_type', 'payroll_bonuses', ['bonus_type'])
    op.create_index('idx_payroll_bonuses_details', 'payroll_bonuses', ['details'], postgresql_using='gin')
    
    # Комментарии
    op.execute("COMMENT ON TABLE payroll_bonuses IS 'Доплаты к зарплате'")
    op.execute("COMMENT ON COLUMN payroll_bonuses.bonus_type IS 'Тип: performance, overtime, manual, other'")
    
    # === 4. EMPLOYEE_PAYMENTS ===
    
    op.create_table(
        'employee_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payroll_entry_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('confirmation_code', sa.String(255), nullable=True),
        sa.Column('payment_details', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['payroll_entry_id'], ['payroll_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для employee_payments
    op.create_index('idx_employee_payments_id', 'employee_payments', ['id'])
    op.create_index('idx_employee_payments_payroll_entry_id', 'employee_payments', ['payroll_entry_id'])
    op.create_index('idx_employee_payments_employee_id', 'employee_payments', ['employee_id'])
    op.create_index('idx_employee_payments_payment_date', 'employee_payments', ['payment_date'])
    op.create_index('idx_employee_payments_status', 'employee_payments', ['status'])
    op.create_index('idx_employee_payments_payment_details', 'employee_payments', ['payment_details'], postgresql_using='gin')
    
    # Комментарии
    op.execute("COMMENT ON TABLE employee_payments IS 'Факты выплат сотрудникам'")
    op.execute("COMMENT ON COLUMN employee_payments.payment_method IS 'Способ: cash, bank_transfer, card, other'")
    op.execute("COMMENT ON COLUMN employee_payments.status IS 'Статус: pending, completed, failed'")


def downgrade() -> None:
    """Откат: удаление таблиц payroll."""
    
    # Удаляем в обратном порядке (из-за FK)
    
    # Employee payments
    op.drop_index('idx_employee_payments_payment_details', table_name='employee_payments')
    op.drop_index('idx_employee_payments_status', table_name='employee_payments')
    op.drop_index('idx_employee_payments_payment_date', table_name='employee_payments')
    op.drop_index('idx_employee_payments_employee_id', table_name='employee_payments')
    op.drop_index('idx_employee_payments_payroll_entry_id', table_name='employee_payments')
    op.drop_index('idx_employee_payments_id', table_name='employee_payments')
    op.drop_table('employee_payments')
    
    # Bonuses
    op.drop_index('idx_payroll_bonuses_details', table_name='payroll_bonuses')
    op.drop_index('idx_payroll_bonuses_bonus_type', table_name='payroll_bonuses')
    op.drop_index('idx_payroll_bonuses_payroll_entry_id', table_name='payroll_bonuses')
    op.drop_index('idx_payroll_bonuses_id', table_name='payroll_bonuses')
    op.drop_table('payroll_bonuses')
    
    # Deductions
    op.drop_index('idx_payroll_deductions_details', table_name='payroll_deductions')
    op.drop_index('idx_payroll_deductions_is_automatic', table_name='payroll_deductions')
    op.drop_index('idx_payroll_deductions_deduction_type', table_name='payroll_deductions')
    op.drop_index('idx_payroll_deductions_payroll_entry_id', table_name='payroll_deductions')
    op.drop_index('idx_payroll_deductions_id', table_name='payroll_deductions')
    op.drop_table('payroll_deductions')
    
    # Entries
    op.drop_index('idx_payroll_entries_calculation_details', table_name='payroll_entries')
    op.drop_index('idx_payroll_entries_period_end', table_name='payroll_entries')
    op.drop_index('idx_payroll_entries_period_start', table_name='payroll_entries')
    op.drop_index('idx_payroll_entries_object_id', table_name='payroll_entries')
    op.drop_index('idx_payroll_entries_contract_id', table_name='payroll_entries')
    op.drop_index('idx_payroll_entries_employee_id', table_name='payroll_entries')
    op.drop_index('idx_payroll_entries_id', table_name='payroll_entries')
    op.drop_table('payroll_entries')
