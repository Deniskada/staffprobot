"""Добавление registration_address_id в профили ЮЛ.

Revision ID: add_regaddr_to_legal_260128
Revises: add_resaddr_to_ind_prof_260128
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_regaddr_to_legal_260128"
down_revision: Union[str, Sequence[str], None] = "add_resaddr_to_ind_prof_260128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить колонку registration_address_id в legal_profiles."""
    op.add_column(
        "legal_profiles",
        sa.Column(
            "registration_address_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_legal_profiles_registration_address_id_addresses",
        "legal_profiles",
        "addresses",
        ["registration_address_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Убрать колонку registration_address_id из legal_profiles."""
    op.drop_constraint(
        "fk_legal_profiles_registration_address_id_addresses",
        "legal_profiles",
        type_="foreignkey",
    )
    op.drop_column("legal_profiles", "registration_address_id")

