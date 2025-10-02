"""Добавить индексы для оптимизации календаря

Revision ID: 067655939741
Revises: 4eeb3651a410
Create Date: 2025-10-02 14:49:55.730645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '067655939741'
down_revision: Union[str, Sequence[str], None] = '4eeb3651a410'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Индексы для таблицы time_slots
    op.create_index('ix_time_slots_object_date_active', 'time_slots', 
                   ['object_id', 'slot_date', 'is_active'], 
                   unique=False)
    
    op.create_index('ix_time_slots_date_range', 'time_slots', 
                   ['slot_date'], 
                   unique=False)
    
    # Индексы для таблицы shift_schedules
    op.create_index('ix_shift_schedules_object_planned_start', 'shift_schedules', 
                   ['object_id', 'planned_start'], 
                   unique=False)
    
    op.create_index('ix_shift_schedules_status_actual_shift', 'shift_schedules', 
                   ['status', 'actual_shift_id'], 
                   unique=False)
    
    op.create_index('ix_shift_schedules_planned_start_range', 'shift_schedules', 
                   ['planned_start'], 
                   unique=False)
    
    # Индексы для таблицы shifts
    op.create_index('ix_shifts_object_start_time', 'shifts', 
                   ['object_id', 'start_time'], 
                   unique=False)
    
    op.create_index('ix_shifts_status_start_time', 'shifts', 
                   ['status', 'start_time'], 
                   unique=False)
    
    op.create_index('ix_shifts_schedule_id', 'shifts', 
                   ['schedule_id'], 
                   unique=False)
    
    op.create_index('ix_shifts_start_time_range', 'shifts', 
                   ['start_time'], 
                   unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы в обратном порядке
    op.drop_index('ix_shifts_start_time_range', table_name='shifts')
    op.drop_index('ix_shifts_schedule_id', table_name='shifts')
    op.drop_index('ix_shifts_status_start_time', table_name='shifts')
    op.drop_index('ix_shifts_object_start_time', table_name='shifts')
    
    op.drop_index('ix_shift_schedules_planned_start_range', table_name='shift_schedules')
    op.drop_index('ix_shift_schedules_status_actual_shift', table_name='shift_schedules')
    op.drop_index('ix_shift_schedules_object_planned_start', table_name='shift_schedules')
    
    op.drop_index('ix_time_slots_date_range', table_name='time_slots')
    op.drop_index('ix_time_slots_object_date_active', table_name='time_slots')
