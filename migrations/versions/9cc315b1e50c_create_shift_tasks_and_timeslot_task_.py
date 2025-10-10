"""create_shift_tasks_and_timeslot_task_templates

Создание таблиц для задач на смену и шаблонов задач для тайм-слотов.

Revision ID: 9cc315b1e50c
Revises: 0e923f2961bb
Create Date: 2025-10-09 21:04:58.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cc315b1e50c'
down_revision: Union[str, Sequence[str], None] = '0e923f2961bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблиц shift_tasks и timeslot_task_templates."""
    
    # === 1. SHIFT_TASKS ===
    
    op.create_table(
        'shift_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('task_text', sa.Text(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для shift_tasks
    op.create_index('idx_shift_tasks_id', 'shift_tasks', ['id'])
    op.create_index('idx_shift_tasks_shift_id', 'shift_tasks', ['shift_id'])
    op.create_index('idx_shift_tasks_is_completed', 'shift_tasks', ['is_completed'])
    op.create_index('idx_shift_tasks_source', 'shift_tasks', ['source'])
    
    # Комментарии
    op.execute("COMMENT ON TABLE shift_tasks IS 'Задачи на смену'")
    op.execute("COMMENT ON COLUMN shift_tasks.source IS 'Источник задачи: object, timeslot, manual'")
    op.execute("COMMENT ON COLUMN shift_tasks.source_id IS 'ID источника (объекта/тайм-слота)'")
    
    # === 2. TIMESLOT_TASK_TEMPLATES ===
    
    op.create_table(
        'timeslot_task_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timeslot_id', sa.Integer(), nullable=False),
        sa.Column('task_text', sa.Text(), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['timeslot_id'], ['time_slots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для timeslot_task_templates
    op.create_index('idx_timeslot_task_templates_id', 'timeslot_task_templates', ['id'])
    op.create_index('idx_timeslot_task_templates_timeslot_id', 'timeslot_task_templates', ['timeslot_id'])
    
    # Комментарии
    op.execute("COMMENT ON TABLE timeslot_task_templates IS 'Шаблоны задач для тайм-слотов'")
    op.execute("COMMENT ON COLUMN timeslot_task_templates.display_order IS 'Порядок отображения задач'")


def downgrade() -> None:
    """Откат: удаление таблиц shift_tasks и timeslot_task_templates."""
    
    # Удалить timeslot_task_templates
    op.drop_index('idx_timeslot_task_templates_timeslot_id', table_name='timeslot_task_templates')
    op.drop_index('idx_timeslot_task_templates_id', table_name='timeslot_task_templates')
    op.drop_table('timeslot_task_templates')
    
    # Удалить shift_tasks
    op.drop_index('idx_shift_tasks_source', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_is_completed', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_shift_id', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_id', table_name='shift_tasks')
    op.drop_table('shift_tasks')
