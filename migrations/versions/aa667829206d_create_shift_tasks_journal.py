"""create_shift_tasks_journal

Revision ID: aa667829206d
Revises: 47854ebf33dc
Create Date: 2025-10-17 17:00:38.159533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa667829206d'
down_revision: Union[str, Sequence[str], None] = '47854ebf33dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы shift_tasks (журнал задач смен)."""
    
    op.create_table(
        'shift_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('task_text', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('requires_media', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deduction_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('is_completed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('media_refs', sa.JSON(), nullable=True),
        sa.Column('correction_ref', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы
    op.create_index('idx_shift_tasks_id', 'shift_tasks', ['id'])
    op.create_index('idx_shift_tasks_shift_id', 'shift_tasks', ['shift_id'])
    op.create_index('idx_shift_tasks_is_completed', 'shift_tasks', ['is_completed'])
    op.create_index('idx_shift_tasks_source', 'shift_tasks', ['source'])
    op.create_index('idx_shift_tasks_is_mandatory', 'shift_tasks', ['is_mandatory'])
    
    # Комментарии
    op.execute("COMMENT ON TABLE shift_tasks IS 'Журнал задач смен (конфигурация + статусы выполнения)'")
    op.execute("COMMENT ON COLUMN shift_tasks.source IS 'Источник задачи: object, timeslot, manual'")
    op.execute("COMMENT ON COLUMN shift_tasks.source_id IS 'ID источника (объекта/тайм-слота)'")
    op.execute("COMMENT ON COLUMN shift_tasks.deduction_amount IS 'Сумма штрафа/премии за невыполнение/выполнение'")
    op.execute("COMMENT ON COLUMN shift_tasks.media_refs IS 'JSON ссылки на медиа-отчеты'")
    op.execute("COMMENT ON COLUMN shift_tasks.correction_ref IS 'ID записи корректировки начисления (связь с payroll_adjustments)'")
    op.execute("COMMENT ON COLUMN shift_tasks.cost IS 'Фактическая премия/штраф по задаче'")


def downgrade() -> None:
    """Откат: удаление таблицы shift_tasks."""
    
    op.drop_index('idx_shift_tasks_is_mandatory', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_source', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_is_completed', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_shift_id', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_id', table_name='shift_tasks')
    op.drop_table('shift_tasks')
