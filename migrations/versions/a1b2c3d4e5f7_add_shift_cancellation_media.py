"""add shift_cancellation_media table (restruct1 Phase 1.4)

Revision ID: a1b2c3d4e5f7
Revises: 119e369385ac
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "119e369385ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shift_cancellation_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "cancellation_id",
            sa.Integer(),
            sa.ForeignKey("shift_cancellations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shift_cancellation_media_cancellation_id",
        "shift_cancellation_media",
        ["cancellation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shift_cancellation_media_cancellation_id",
        table_name="shift_cancellation_media",
    )
    op.drop_table("shift_cancellation_media")
