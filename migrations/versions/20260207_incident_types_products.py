"""Типы тикетов, справочник товаров, позиции обращений.

Revision ID: incident_types_260207
Revises: phase3_260130
Create Date: 2026-02-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "incident_types_260207"
down_revision: Union[str, Sequence[str], None] = "phase3_260130"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Таблица products ---
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default="шт."),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 2. Таблица incident_items ---
    op.create_table(
        "incident_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False, server_default="1"),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("modified_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 3. Новые поля в incidents ---
    op.add_column("incidents", sa.Column("incident_type", sa.String(50), nullable=True))
    op.add_column("incidents", sa.Column("compensate_purchase", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # Backfill: все существующие инциденты → тип "deduction"
    op.execute(text("UPDATE incidents SET incident_type = 'deduction' WHERE incident_type IS NULL"))

    # Теперь делаем NOT NULL
    op.alter_column("incidents", "incident_type", nullable=False, server_default="deduction")
    op.create_index("ix_incidents_incident_type", "incidents", ["incident_type"])

    # --- 4. Новое поле в incident_categories ---
    op.add_column("incident_categories", sa.Column("incident_type", sa.String(50), nullable=True))

    # Backfill: все существующие категории → тип "deduction"
    op.execute(text("UPDATE incident_categories SET incident_type = 'deduction' WHERE incident_type IS NULL"))

    # Теперь делаем NOT NULL
    op.alter_column("incident_categories", "incident_type", nullable=False, server_default="deduction")
    op.create_index("ix_incident_categories_incident_type", "incident_categories", ["incident_type"])


def downgrade() -> None:
    op.drop_index("ix_incident_categories_incident_type", table_name="incident_categories")
    op.drop_column("incident_categories", "incident_type")
    op.drop_index("ix_incidents_incident_type", table_name="incidents")
    op.drop_column("incidents", "compensate_purchase")
    op.drop_column("incidents", "incident_type")
    op.drop_table("incident_items")
    op.drop_table("products")
