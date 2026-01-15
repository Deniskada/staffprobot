"""change_contract_history_change_type_to_string

Revision ID: 7d8bbe751a44
Revises: 8fd436f68bd3
Create Date: 2026-01-15 14:49:31.675280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d8bbe751a44'
down_revision: Union[str, Sequence[str], None] = '8fd436f68bd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Изменяем тип колонки change_type с enum на varchar
    op.execute("""
        ALTER TABLE contract_history 
        ALTER COLUMN change_type TYPE VARCHAR(50) 
        USING change_type::text;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Возвращаем enum тип (если enum еще существует)
    op.execute("""
        ALTER TABLE contract_history 
        ALTER COLUMN change_type TYPE contract_change_type 
        USING change_type::contract_change_type;
    """)
