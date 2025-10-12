"""create_payment_systems_table

Создание справочника видов систем оплаты труда с seed-данными.

Revision ID: b6c9fd9375d0
Revises: 37fffd12f510
Create Date: 2025-10-09 14:10:28.474545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c9fd9375d0'
down_revision: Union[str, Sequence[str], None] = '37fffd12f510'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы payment_systems и заполнение seed-данными."""
    
    # Создать таблицу
    op.create_table(
        'payment_systems',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('calculation_type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создать индексы
    op.create_index('idx_payment_systems_id', 'payment_systems', ['id'])
    op.create_index('idx_payment_systems_code', 'payment_systems', ['code'], unique=True)
    op.create_index('idx_payment_systems_is_active', 'payment_systems', ['is_active'])
    op.create_index('idx_payment_systems_display_order', 'payment_systems', ['display_order'])
    
    # Добавить комментарии
    op.execute("COMMENT ON TABLE payment_systems IS 'Справочник видов систем оплаты труда'")
    op.execute("COMMENT ON COLUMN payment_systems.code IS 'Уникальный код системы (simple_hourly, salary, hourly_bonus)'")
    op.execute("COMMENT ON COLUMN payment_systems.calculation_type IS 'Тип расчета (hourly, salary, hourly_bonus)'")
    
    # Заполнить seed-данные
    op.execute("""
        INSERT INTO payment_systems (code, name, description, calculation_type, display_order)
        VALUES 
        (
            'simple_hourly',
            'Простая повременная',
            'Оплата за фактически отработанное время по часовой ставке',
            'hourly',
            1
        ),
        (
            'salary',
            'Окладная',
            'Фиксированная ежемесячная оплата труда, не зависящая от количества выполненной работы',
            'salary',
            2
        ),
        (
            'hourly_bonus',
            'Повременно-премиальная',
            'Оплата времени работы плюс премия за достижение показателей или демотивация за нарушения',
            'hourly_bonus',
            3
        )
    """)


def downgrade() -> None:
    """Откат: удаление таблицы payment_systems."""
    
    # Удалить индексы
    op.drop_index('idx_payment_systems_display_order', table_name='payment_systems')
    op.drop_index('idx_payment_systems_is_active', table_name='payment_systems')
    op.drop_index('idx_payment_systems_code', table_name='payment_systems')
    op.drop_index('idx_payment_systems_id', table_name='payment_systems')
    
    # Удалить таблицу
    op.drop_table('payment_systems')
