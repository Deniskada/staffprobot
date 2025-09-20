"""fix_user_role_defaults

Revision ID: fix_user_role_defaults
Revises: 8fd55f2cd4ee
Create Date: 2025-09-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_user_role_defaults'
down_revision: Union[str, Sequence[str], None] = '8fd55f2cd4ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Удаляем значения по умолчанию для полей role и roles
    op.alter_column('users', 'role',
                   existing_type=sa.String(50),
                   nullable=False,
                   server_default=None)
    
    op.alter_column('users', 'roles',
                   existing_type=sa.JSON(),
                   nullable=False,
                   server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Восстанавливаем значения по умолчанию
    op.alter_column('users', 'role',
                   existing_type=sa.String(50),
                   nullable=False,
                   server_default=sa.text("'applicant'"))
    
    op.alter_column('users', 'roles',
                   existing_type=sa.JSON(),
                   nullable=False,
                   server_default=sa.text("'[\"applicant\"]'::json"))
