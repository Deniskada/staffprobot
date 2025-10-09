"""create_payment_schedules_table

Создание таблицы графиков выплат с seed-данными.

Revision ID: 5d3d105cbbe1
Revises: 97d3b944c0b9
Create Date: 2025-10-09 14:55:29.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5d3d105cbbe1'
down_revision: Union[str, Sequence[str], None] = '97d3b944c0b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы payment_schedules и заполнение seed-данными."""
    
    # Создать таблицу
    op.create_table(
        'payment_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('frequency', sa.String(50), nullable=False),
        sa.Column('payment_period', postgresql.JSONB(), nullable=False),
        sa.Column('payment_day', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создать индексы
    op.create_index('idx_payment_schedules_id', 'payment_schedules', ['id'])
    op.create_index('idx_payment_schedules_frequency', 'payment_schedules', ['frequency'])
    op.create_index('idx_payment_schedules_is_active', 'payment_schedules', ['is_active'])
    op.create_index('idx_payment_schedules_payment_period', 'payment_schedules', ['payment_period'], postgresql_using='gin')
    
    # Добавить комментарии
    op.execute("COMMENT ON TABLE payment_schedules IS 'Графики выплат'")
    op.execute("COMMENT ON COLUMN payment_schedules.frequency IS 'Частота выплат (weekly, biweekly, monthly)'")
    op.execute("COMMENT ON COLUMN payment_schedules.payment_period IS 'Период расчета в формате JSON: {type, description, calc_rules}'")
    op.execute("COMMENT ON COLUMN payment_schedules.payment_day IS 'День выплаты: для weekly (1-7), для monthly (1-31)'")
    
    # Заполнить seed-данные
    op.execute("""
        INSERT INTO payment_schedules (name, description, frequency, payment_day, payment_period)
        VALUES 
        (
            'Еженедельно по пятницам',
            'Выплата каждую пятницу за предыдущую неделю (понедельник-воскресенье)',
            'weekly',
            5,
            '{"type": "week", "description": "За предыдущую неделю (понедельник-воскресенье)", "calc_rules": {"period": "previous_week", "start_day": "monday", "end_day": "sunday"}}'::jsonb
        ),
        (
            'Два раза в месяц (15-е и 30-е)',
            'Выплата 15-го за период с 16-го прошлого месяца по 15-е текущего, 30-го за период с 16-го по 30-е текущего месяца',
            'biweekly',
            15,
            '{"type": "month", "description": "Две выплаты в месяц", "calc_rules": {"first_payment": {"day": 15, "period": "16-end_of_previous_month_to_15", "description": "За период с 16-го прошлого месяца по 15-е текущего"}, "second_payment": {"day": 30, "period": "16-30", "description": "За период с 16-го по 30-е (или конец месяца) текущего месяца"}}}'::jsonb
        ),
        (
            'Ежемесячно 5-го числа',
            'Выплата 5-го числа каждого месяца за весь предыдущий месяц',
            'monthly',
            5,
            '{"type": "month", "description": "За весь предыдущий месяц (с 1-го по последнее число)", "calc_rules": {"period": "previous_month", "start_day": 1, "end_day": "last_day_of_month"}}'::jsonb
        )
    """)


def downgrade() -> None:
    """Откат: удаление таблицы payment_schedules."""
    
    # Удалить индексы
    op.drop_index('idx_payment_schedules_payment_period', table_name='payment_schedules')
    op.drop_index('idx_payment_schedules_is_active', table_name='payment_schedules')
    op.drop_index('idx_payment_schedules_frequency', table_name='payment_schedules')
    op.drop_index('idx_payment_schedules_id', table_name='payment_schedules')
    
    # Удалить таблицу
    op.drop_table('payment_schedules')
