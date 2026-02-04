"""Конструктор шаблонов: contract_types, constructor_flows, steps, fragments; расширение contract_templates.

Revision ID: constructor_flows_260129
Revises: add_regaddr_to_legal_260128
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "constructor_flows_260129"
down_revision: Union[str, Sequence[str], None] = "add_regaddr_to_legal_260128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contract_types_code", "contract_types", ["code"], unique=True)
    op.create_index("ix_contract_types_id", "contract_types", ["id"], unique=False)

    op.create_table(
        "constructor_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("source_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["contract_type_id"], ["contract_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_constructor_flows_contract_type_id", "constructor_flows", ["contract_type_id"], unique=False)
    op.create_index("ix_constructor_flows_id", "constructor_flows", ["id"], unique=False)

    op.create_table(
        "constructor_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flow_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("schema", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("request_at_conclusion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["flow_id"], ["constructor_flows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flow_id", "slug", name="uq_constructor_steps_flow_slug"),
    )
    op.create_index("ix_constructor_steps_flow_id", "constructor_steps", ["flow_id"], unique=False)
    op.create_index("ix_constructor_steps_id", "constructor_steps", ["id"], unique=False)

    op.create_table(
        "constructor_fragments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("option_key", sa.String(128), nullable=True),
        sa.Column("fragment_content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["constructor_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_constructor_fragments_step_id", "constructor_fragments", ["step_id"], unique=False)
    op.create_index("ix_constructor_fragments_id", "constructor_fragments", ["id"], unique=False)

    op.add_column(
        "contract_templates",
        sa.Column("contract_type_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "contract_templates",
        sa.Column("constructor_flow_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_contract_templates_contract_type_id",
        "contract_templates",
        "contract_types",
        ["contract_type_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_contract_templates_constructor_flow_id",
        "contract_templates",
        "constructor_flows",
        ["constructor_flow_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_contract_templates_contract_type_id", "contract_templates", ["contract_type_id"], unique=False)
    op.create_index("ix_contract_templates_constructor_flow_id", "contract_templates", ["constructor_flow_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contract_templates_constructor_flow_id", table_name="contract_templates")
    op.drop_index("ix_contract_templates_contract_type_id", table_name="contract_templates")
    op.drop_constraint("fk_contract_templates_constructor_flow_id", "contract_templates", type_="foreignkey")
    op.drop_constraint("fk_contract_templates_contract_type_id", "contract_templates", type_="foreignkey")
    op.drop_column("contract_templates", "constructor_flow_id")
    op.drop_column("contract_templates", "contract_type_id")

    op.drop_index("ix_constructor_fragments_id", table_name="constructor_fragments")
    op.drop_index("ix_constructor_fragments_step_id", table_name="constructor_fragments")
    op.drop_table("constructor_fragments")

    op.drop_index("ix_constructor_steps_id", table_name="constructor_steps")
    op.drop_index("ix_constructor_steps_flow_id", table_name="constructor_steps")
    op.drop_table("constructor_steps")

    op.drop_index("ix_constructor_flows_id", table_name="constructor_flows")
    op.drop_index("ix_constructor_flows_contract_type_id", table_name="constructor_flows")
    op.drop_table("constructor_flows")

    op.drop_index("ix_contract_types_id", table_name="contract_types")
    op.drop_index("ix_contract_types_code", table_name="contract_types")
    op.drop_table("contract_types")
