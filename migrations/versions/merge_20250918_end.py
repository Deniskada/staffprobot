"""Merge remaining heads to single head

Revision ID: merge_20250918_end
Revises: merge_20250918_final, 2e5b72ddefec
Create Date: 2025-09-18 00:25:00

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401


revision: str = "merge_20250918_end"
down_revision: Union[str, Sequence[str], None] = (
    "merge_20250918_final",
    "2e5b72ddefec",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


