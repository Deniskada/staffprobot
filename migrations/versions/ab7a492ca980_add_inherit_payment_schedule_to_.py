"""add_inherit_payment_schedule_to_contracts

Revision ID: ab7a492ca980
Revises: c4fe42990441
Create Date: 2025-12-02 11:51:52.743115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab7a492ca980'
down_revision: Union[str, Sequence[str], None] = 'c4fe42990441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле inherit_payment_schedule в таблицу contracts
    op.add_column('contracts', 
        sa.Column('inherit_payment_schedule', sa.Boolean(), 
                  nullable=False, server_default='true'))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле inherit_payment_schedule из таблицы contracts
    op.drop_column('contracts', 'inherit_payment_schedule')
