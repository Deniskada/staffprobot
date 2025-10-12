"""create_payroll_adjustments_drop_old_tables

Revision ID: e6381c327d9e
Revises: c4ea4d69992c
Create Date: 2025-10-10 22:38:09.501778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e6381c327d9e'
down_revision: Union[str, Sequence[str], None] = 'c4ea4d69992c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Phase 4A: Рефакторинг системы начислений
    - Создать единую таблицу payroll_adjustments
    - Удалить старые таблицы shift_tasks, payroll_deductions, payroll_bonuses
    """
    # Создать таблицу payroll_adjustments
    op.create_table(
        'payroll_adjustments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.Column('adjustment_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('payroll_entry_id', sa.Integer(), nullable=True),
        sa.Column('is_applied', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('edit_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['object_id'], ['objects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payroll_entry_id'], ['payroll_entries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Создать индексы
    op.create_index('idx_payroll_adjustments_employee_id', 'payroll_adjustments', ['employee_id'])
    op.create_index('idx_payroll_adjustments_shift_id', 'payroll_adjustments', ['shift_id'])
    op.create_index('idx_payroll_adjustments_object_id', 'payroll_adjustments', ['object_id'])
    op.create_index('idx_payroll_adjustments_adjustment_type', 'payroll_adjustments', ['adjustment_type'])
    op.create_index('idx_payroll_adjustments_is_applied', 'payroll_adjustments', ['is_applied'])
    op.create_index('idx_payroll_adjustments_payroll_entry_id', 'payroll_adjustments', ['payroll_entry_id'])
    op.create_index('idx_payroll_adjustments_created_by', 'payroll_adjustments', ['created_by'])
    op.create_index('idx_payroll_adjustments_updated_by', 'payroll_adjustments', ['updated_by'])
    op.create_index('idx_payroll_adjustments_created_at', 'payroll_adjustments', ['created_at'])
    
    # Добавить комментарий к таблице
    op.execute("""
        COMMENT ON TABLE payroll_adjustments IS 'Единая таблица корректировок начислений (смены, штрафы, премии, задачи)';
        COMMENT ON COLUMN payroll_adjustments.adjustment_type IS 'Тип корректировки: shift_base, late_start, task_bonus, task_penalty, manual_bonus, manual_deduction';
        COMMENT ON COLUMN payroll_adjustments.amount IS 'Сумма корректировки (может быть + или -)';
        COMMENT ON COLUMN payroll_adjustments.is_applied IS 'Применено к payroll_entry';
        COMMENT ON COLUMN payroll_adjustments.edit_history IS 'История изменений [{timestamp, user_id, field, old_value, new_value}]';
    """)
    
    # Удалить старые таблицы (порядок важен из-за FK)
    op.drop_table('shift_tasks')
    op.drop_table('payroll_bonuses')
    op.drop_table('payroll_deductions')


def downgrade() -> None:
    """
    Откат миграции - восстановить старые таблицы
    ВНИМАНИЕ: Данные из payroll_adjustments будут потеряны!
    """
    # Восстановить payroll_deductions
    op.create_table(
        'payroll_deductions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payroll_entry_id', sa.Integer(), nullable=False),
        sa.Column('deduction_type', sa.String(length=50), nullable=False),
        sa.Column('is_automatic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payroll_entry_id'], ['payroll_entries.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_payroll_deductions_payroll_entry_id', 'payroll_deductions', ['payroll_entry_id'])
    op.create_index('idx_payroll_deductions_deduction_type', 'payroll_deductions', ['deduction_type'])
    op.create_index('idx_payroll_deductions_is_automatic', 'payroll_deductions', ['is_automatic'])
    
    # Восстановить payroll_bonuses
    op.create_table(
        'payroll_bonuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payroll_entry_id', sa.Integer(), nullable=False),
        sa.Column('bonus_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payroll_entry_id'], ['payroll_entries.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_payroll_bonuses_payroll_entry_id', 'payroll_bonuses', ['payroll_entry_id'])
    op.create_index('idx_payroll_bonuses_bonus_type', 'payroll_bonuses', ['bonus_type'])
    
    # Восстановить shift_tasks
    op.create_table(
        'shift_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('task_text', sa.Text(), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deduction_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_shift_tasks_shift_id', 'shift_tasks', ['shift_id'])
    op.create_index('idx_shift_tasks_is_completed', 'shift_tasks', ['is_completed'])
    
    # Удалить новую таблицу
    op.drop_table('payroll_adjustments')
