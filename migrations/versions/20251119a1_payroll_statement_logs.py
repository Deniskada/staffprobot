"""Add payroll_statement_logs table.

Revision ID: 20251119a1
Revises: 0827df3c36e3
Create Date: 2025-11-19 11:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20251119a1"
down_revision: Union[str, None] = "0827df3c36e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payroll_statement_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_role", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total_net", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_paid", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_payroll_statement_logs_employee_id",
        "payroll_statement_logs",
        ["employee_id"],
    )
    op.create_index(
        "ix_payroll_statement_logs_owner_id",
        "payroll_statement_logs",
        ["owner_id"],
    )
    op.create_index(
        "ix_payroll_statement_logs_requested_by",
        "payroll_statement_logs",
        ["requested_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_payroll_statement_logs_requested_by", table_name="payroll_statement_logs")
    op.drop_index("ix_payroll_statement_logs_owner_id", table_name="payroll_statement_logs")
    op.drop_index("ix_payroll_statement_logs_employee_id", table_name="payroll_statement_logs")
    op.drop_table("payroll_statement_logs")

