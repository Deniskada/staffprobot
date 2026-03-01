"""Добавить поле expires_at в contracts.

Revision ID: contract_expires_at_260223
Revises: offer_edo_260215
Create Date: 2026-02-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "contract_expires_at_260223"
down_revision: Union[str, Sequence[str], None] = "20260301_merge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Срок действия оферты, после которого автоматически истекает",
        ),
    )


def downgrade() -> None:
    op.drop_column("contracts", "expires_at")
