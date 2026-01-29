"""Добавление residence_address_id в индивидуальные профили.

Revision ID: add_resaddr_to_ind_prof_260128
Revises: add_userid_to_addresses_260128
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_resaddr_to_ind_prof_260128"
down_revision: Union[str, Sequence[str], None] = "add_userid_to_addresses_260128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить колонку residence_address_id в individual_profiles."""
    op.add_column(
        "individual_profiles",
        sa.Column("residence_address_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_individual_profiles_residence_address_id_addresses",
        "individual_profiles",
        "addresses",
        ["residence_address_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Удалить колонку residence_address_id."""
    op.drop_constraint(
        "fk_individual_profiles_residence_address_id_addresses",
        "individual_profiles",
        type_="foreignkey",
    )
    op.drop_column("individual_profiles", "residence_address_id")

