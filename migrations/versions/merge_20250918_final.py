"""Final merge to single head

Revision ID: merge_20250918_final
Revises: merge_20250918_unify_heads, 20250828_add_time_slots_table
Create Date: 2025-09-18 00:15:00

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401


revision: str = "merge_20250918_final"
down_revision: Union[str, Sequence[str], None] = (
    "merge_20250918_unify_heads",
    "20250828_add_time_slots_table",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


