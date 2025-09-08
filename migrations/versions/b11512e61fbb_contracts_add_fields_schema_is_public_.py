"""contracts: add fields_schema,is_public to templates; values,content nullable

Revision ID: b11512e61fbb
Revises: 187db2e835ad
Create Date: 2025-09-08 12:15:17.769628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b11512e61fbb'
down_revision: Union[str, Sequence[str], None] = '187db2e835ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новые поля к contract_templates
    op.add_column('contract_templates', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('contract_templates', sa.Column('fields_schema', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    # Делаем поле content в contracts nullable и добавляем values JSON
    op.alter_column('contracts', 'content', existing_type=sa.TEXT(), nullable=True)
    op.add_column('contracts', sa.Column('values', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    # Убираем server_default, оставляя значение столбца
    op.alter_column('contract_templates', 'is_public', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Откат изменений
    op.drop_column('contracts', 'values')
    op.alter_column('contracts', 'content', existing_type=sa.TEXT(), nullable=False)
    op.drop_column('contract_templates', 'fields_schema')
    op.drop_column('contract_templates', 'is_public')
