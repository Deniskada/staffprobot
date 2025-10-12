"""add_use_contract_payment_system_to_contracts

Revision ID: c4ea4d69992c
Revises: 5d83e2a89e52
Create Date: 2025-10-10 18:59:41.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4ea4d69992c'
down_revision = '5d83e2a89e52'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Добавляет поле use_contract_payment_system в таблицу contracts.
    
    Аналогично use_contract_rate, этот флаг определяет приоритет системы оплаты:
    - Если True: используется payment_system_id из договора
    - Если False: используется payment_system_id объекта (с наследованием от подразделения)
    """
    # Добавить столбец use_contract_payment_system
    op.add_column(
        'contracts',
        sa.Column('use_contract_payment_system', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Создать индекс для оптимизации запросов
    op.create_index(
        'idx_contracts_use_contract_payment_system',
        'contracts',
        ['use_contract_payment_system']
    )
    
    # Добавить комментарий к столбцу
    op.execute(
        "COMMENT ON COLUMN contracts.use_contract_payment_system IS "
        "'Приоритет системы оплаты из договора (аналог use_contract_rate)'"
    )


def downgrade() -> None:
    """Откат миграции."""
    op.drop_index('idx_contracts_use_contract_payment_system', table_name='contracts')
    op.drop_column('contracts', 'use_contract_payment_system')
