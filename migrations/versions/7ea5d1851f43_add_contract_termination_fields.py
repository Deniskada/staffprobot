"""add_contract_termination_fields

Revision ID: 7ea5d1851f43
Revises: da5277f32d13
Create Date: 2025-10-19 20:19:07.524539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ea5d1851f43'
down_revision: Union[str, Sequence[str], None] = 'da5277f32d13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле termination_date
    op.add_column('contracts', sa.Column('termination_date', sa.Date(), nullable=True))
    
    # Добавляем поле settlement_policy с дефолтом
    op.add_column(
        'contracts',
        sa.Column(
            'settlement_policy',
            sa.String(length=32),
            nullable=False,
            server_default='schedule'
        )
    )
    
    # Создаём индекс для settlement_policy
    op.create_index(
        'ix_contracts_settlement_policy',
        'contracts',
        ['settlement_policy'],
        unique=False
    )
    
    # Убираем server_default после применения, чтобы не висел в схеме
    op.alter_column('contracts', 'settlement_policy', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индекс
    op.drop_index('ix_contracts_settlement_policy', table_name='contracts')
    
    # Удаляем колонки
    op.drop_column('contracts', 'settlement_policy')
    op.drop_column('contracts', 'termination_date')
