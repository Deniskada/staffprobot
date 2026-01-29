"""Добавление user_id в таблицу адресов.

Revision ID: add_userid_to_addresses_260128
Revises: profiles_and_addresses_20260128
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_userid_to_addresses_260128"
down_revision: Union[str, Sequence[str], None] = "profiles_and_addresses_20260128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить колонку user_id и индекс/FK в addresses."""
    op.add_column(
        "addresses",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_addresses_user_id_users",
        "addresses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Откатить добавление user_id."""
    op.drop_constraint("fk_addresses_user_id_users", "addresses", type_="foreignkey")
    op.drop_index("ix_addresses_user_id", table_name="addresses")
    op.drop_column("addresses", "user_id")

