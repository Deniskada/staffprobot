"""Unify multiple heads into single head

Revision ID: merge_20250918_unify_heads
Revises: 20250917_roles_jsonb_fix, 9e47662cd158, postgis_extension
Create Date: 2025-09-18 00:00:00

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401


revision: str = "merge_20250918_unify_heads"
down_revision: Union[str, Sequence[str], None] = (
    "20250917_roles_jsonb_fix",
    "9e47662cd158",
    "postgis_extension",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration: no-op
    pass


def downgrade() -> None:
    # Merge migration: no-op
    pass


