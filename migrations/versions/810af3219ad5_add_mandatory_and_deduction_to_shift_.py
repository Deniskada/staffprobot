"""add_mandatory_and_deduction_to_shift_tasks

Revision ID: 810af3219ad5
Revises: dcb9f508b8d3
Create Date: 2025-10-10 09:10:25.579374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '810af3219ad5'
down_revision: Union[str, Sequence[str], None] = 'dcb9f508b8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление полей is_mandatory и deduction_amount в shift_tasks и timeslot_task_templates."""
    
    # === 1. SHIFT_TASKS ===
    
    # Добавить is_mandatory
    op.add_column('shift_tasks', sa.Column('is_mandatory', sa.Boolean(), server_default='true', nullable=False))
    
    # Добавить deduction_amount
    op.add_column('shift_tasks', sa.Column('deduction_amount', sa.Numeric(10, 2), nullable=True))
    
    # Создать индексы
    op.create_index('idx_shift_tasks_is_mandatory', 'shift_tasks', ['is_mandatory'])
    
    # Комментарии
    op.execute("COMMENT ON COLUMN shift_tasks.is_mandatory IS 'Обязательная ли задача (при невыполнении - удержание)'")
    op.execute("COMMENT ON COLUMN shift_tasks.deduction_amount IS 'Сумма удержания за невыполнение (в рублях)'")
    
    # === 2. TIMESLOT_TASK_TEMPLATES ===
    
    # Добавить is_mandatory
    op.add_column('timeslot_task_templates', sa.Column('is_mandatory', sa.Boolean(), server_default='true', nullable=False))
    
    # Добавить deduction_amount
    op.add_column('timeslot_task_templates', sa.Column('deduction_amount', sa.Numeric(10, 2), nullable=True))
    
    # Комментарии
    op.execute("COMMENT ON COLUMN timeslot_task_templates.is_mandatory IS 'Обязательная ли задача'")
    op.execute("COMMENT ON COLUMN timeslot_task_templates.deduction_amount IS 'Сумма удержания за невыполнение (в рублях)'")


def downgrade() -> None:
    """Откат: удаление полей is_mandatory и deduction_amount."""
    
    # Удалить из timeslot_task_templates
    op.drop_column('timeslot_task_templates', 'deduction_amount')
    op.drop_column('timeslot_task_templates', 'is_mandatory')
    
    # Удалить из shift_tasks
    op.drop_index('idx_shift_tasks_is_mandatory', table_name='shift_tasks')
    op.drop_column('shift_tasks', 'deduction_amount')
    op.drop_column('shift_tasks', 'is_mandatory')
