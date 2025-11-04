"""add_requires_geolocation_to_task_template_v2

Revision ID: c6b88a3de81e
Revises: 26f081e4388f
Create Date: 2025-11-04 22:18:22.222423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c6b88a3de81e'
down_revision: Union[str, Sequence[str], None] = '26f081e4388f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле requires_geolocation в task_templates_v2
    op.add_column('task_templates_v2', sa.Column('requires_geolocation', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле requires_geolocation из task_templates_v2
    op.drop_column('task_templates_v2', 'requires_geolocation')
