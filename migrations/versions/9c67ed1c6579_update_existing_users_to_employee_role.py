"""update_existing_users_to_employee_role

Revision ID: 9c67ed1c6579
Revises: 3fe3022e79cf
Create Date: 2025-09-06 14:59:35.615827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c67ed1c6579'
down_revision: Union[str, Sequence[str], None] = '3fe3022e79cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Обновляем существующих пользователей, у которых роль NULL или пустая
    op.execute("""
        UPDATE users 
        SET role = 'employee' 
        WHERE role IS NULL OR role = ''
    """)
    
    # Устанавливаем NOT NULL constraint для поля role
    op.alter_column('users', 'role', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Убираем NOT NULL constraint для поля role
    op.alter_column('users', 'role', nullable=True)
