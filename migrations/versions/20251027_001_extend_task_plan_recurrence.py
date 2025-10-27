"""Extend task_plans_v2 with recurrence and time fields

Revision ID: 20251027_001
Revises: 20251022_001
Create Date: 2025-10-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251027_001'
down_revision = '20251022_001'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поля для периодичности и времени в task_plans_v2
    op.add_column('task_plans_v2', sa.Column('recurrence_type', sa.String(20), nullable=True))
    op.add_column('task_plans_v2', sa.Column('recurrence_config', postgresql.JSONB, nullable=True))
    op.add_column('task_plans_v2', sa.Column('recurrence_end_date', sa.Date, nullable=True))
    op.add_column('task_plans_v2', sa.Column('planned_time_start', sa.Time, nullable=True))
    
    # Индексы для ускорения запросов планировщика
    op.create_index('ix_task_plans_v2_recurrence_type', 'task_plans_v2', ['recurrence_type'])
    op.create_index('ix_task_plans_v2_planned_time_start', 'task_plans_v2', ['planned_time_start'])
    
    # Комментарии
    op.execute("""
        COMMENT ON COLUMN task_plans_v2.recurrence_type IS 'once, weekdays, interval, или NULL для постоянных';
        COMMENT ON COLUMN task_plans_v2.recurrence_config IS 'JSON конфиг: {weekdays: [0,1,2]} или {interval_days: 7}';
        COMMENT ON COLUMN task_plans_v2.planned_time_start IS 'Время начала для фильтрации тайм-слотов (HH:MM)';
    """)


def downgrade():
    op.drop_index('ix_task_plans_v2_planned_time_start', 'task_plans_v2')
    op.drop_index('ix_task_plans_v2_recurrence_type', 'task_plans_v2')
    op.drop_column('task_plans_v2', 'planned_time_start')
    op.drop_column('task_plans_v2', 'recurrence_end_date')
    op.drop_column('task_plans_v2', 'recurrence_config')
    op.drop_column('task_plans_v2', 'recurrence_type')

