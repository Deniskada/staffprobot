"""Add PostGIS extension (idempotent)

Revision ID: postgis_extension
Revises: 4b2855b94366
Create Date: 2025-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "postgis_extension"
down_revision: Union[str, Sequence[str], None] = "4b2855b94366"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём только базовое расширение PostGIS; без topology/tiger
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def downgrade() -> None:
    # Безопасный откат: не удаляем расширение в проде
    # Если потребуется, раскомментировать следующую строку
    # op.execute("DROP EXTENSION IF EXISTS postgis;")
    pass


