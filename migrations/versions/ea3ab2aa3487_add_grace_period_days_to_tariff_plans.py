"""add_grace_period_days_to_tariff_plans

Revision ID: ea3ab2aa3487
Revises: 68f07b8a9688
Create Date: 2025-11-01 10:43:24.152511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea3ab2aa3487'
down_revision: Union[str, Sequence[str], None] = '68f07b8a9688'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле grace_period_days в таблицу tariff_plans
    op.add_column('tariff_plans', sa.Column('grace_period_days', sa.Integer(), nullable=True, server_default='0'))
    
    # Устанавливаем значение по умолчанию для существующих записей
    op.execute("UPDATE tariff_plans SET grace_period_days = 0 WHERE grace_period_days IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле grace_period_days
    op.drop_column('tariff_plans', 'grace_period_days')
