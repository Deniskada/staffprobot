"""add_task_v2_fields_to_payroll_adjustment

Revision ID: 483be5c7fa46
Revises: 5056deff776a
Create Date: 2025-10-27 12:39:38.335095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '483be5c7fa46'
down_revision: Union[str, Sequence[str], None] = '5056deff776a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем связи с Tasks v2 и ShiftSchedule
    op.add_column('payroll_adjustments', sa.Column('shift_schedule_id', sa.Integer(), nullable=True))
    op.add_column('payroll_adjustments', sa.Column('task_entry_v2_id', sa.Integer(), nullable=True))
    
    # Создаём индексы
    op.create_index('ix_payroll_adjustments_shift_schedule_id', 'payroll_adjustments', ['shift_schedule_id'])
    op.create_index('ix_payroll_adjustments_task_entry_v2_id', 'payroll_adjustments', ['task_entry_v2_id'])
    
    # Добавляем foreign keys
    op.create_foreign_key(
        'fk_payroll_adjustments_shift_schedule',
        'payroll_adjustments', 'shift_schedules',
        ['shift_schedule_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_payroll_adjustments_task_entry_v2',
        'payroll_adjustments', 'task_entries_v2',
        ['task_entry_v2_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_payroll_adjustments_task_entry_v2', 'payroll_adjustments', type_='foreignkey')
    op.drop_constraint('fk_payroll_adjustments_shift_schedule', 'payroll_adjustments', type_='foreignkey')
    op.drop_index('ix_payroll_adjustments_task_entry_v2_id', 'payroll_adjustments')
    op.drop_index('ix_payroll_adjustments_shift_schedule_id', 'payroll_adjustments')
    op.drop_column('payroll_adjustments', 'task_entry_v2_id')
    op.drop_column('payroll_adjustments', 'shift_schedule_id')
