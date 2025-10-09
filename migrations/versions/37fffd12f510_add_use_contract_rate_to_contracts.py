"""add_use_contract_rate_to_contracts

Добавление флага use_contract_rate для приоритета ставки договора.

Revision ID: 37fffd12f510
Revises: efa5928b82ac
Create Date: 2025-10-09 12:52:13.916565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37fffd12f510'
down_revision: Union[str, Sequence[str], None] = 'efa5928b82ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление use_contract_rate в contracts."""
    
    # Добавить поле use_contract_rate
    op.add_column('contracts', 
        sa.Column('use_contract_rate', sa.Boolean(), server_default='false', nullable=False)
    )
    
    # Создать индекс для оптимизации запросов
    op.create_index(
        'idx_contracts_use_contract_rate', 
        'contracts', 
        ['use_contract_rate']
    )
    
    # Добавить комментарий
    op.execute(
        "COMMENT ON COLUMN contracts.use_contract_rate IS "
        "'Использовать ставку из договора (приоритет над объектом/тайм-слотом)'"
    )


def downgrade() -> None:
    """Откат: удаление use_contract_rate."""
    
    # Удалить индекс
    op.drop_index('idx_contracts_use_contract_rate', table_name='contracts')
    
    # Удалить столбец
    op.drop_column('contracts', 'use_contract_rate')
