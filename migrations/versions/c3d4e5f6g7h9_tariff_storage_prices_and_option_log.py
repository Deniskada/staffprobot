"""tariff storage prices + subscription_option_log (restruct1 Phase 1.6)

Revision ID: c3d4e5f6g7h9
Revises: b2c3d4e5f6g8
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6g7h9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tariff_plans",
        sa.Column("storage_price_telegram", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "tariff_plans",
        sa.Column("storage_price_object_storage", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "tariff_plans",
        sa.Column("storage_option_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    op.create_table(
        "subscription_option_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("user_subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("old_tariff_id", sa.Integer(), sa.ForeignKey("tariff_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("new_tariff_id", sa.Integer(), sa.ForeignKey("tariff_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("options_enabled", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("options_disabled", sa.JSON(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_option_log_subscription_id", "subscription_option_log", ["subscription_id"])
    op.create_index("ix_subscription_option_log_changed_at", "subscription_option_log", ["changed_at"])


def downgrade() -> None:
    op.drop_index("ix_subscription_option_log_changed_at", table_name="subscription_option_log")
    op.drop_index("ix_subscription_option_log_subscription_id", table_name="subscription_option_log")
    op.drop_table("subscription_option_log")
    op.drop_column("tariff_plans", "storage_option_price")
    op.drop_column("tariff_plans", "storage_price_object_storage")
    op.drop_column("tariff_plans", "storage_price_telegram")
