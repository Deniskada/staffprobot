"""Добавление таблиц адресов и профилей пользователей (ФЛ, ИП, ЮЛ).

Revision ID: profiles_and_addresses_20260128
Revises: final_deployment
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "profiles_and_addresses_20260128"
down_revision: Union[str, Sequence[str], None] = "da1eedda616f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create addresses and profile tables."""
    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="Россия"),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=False),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("house", sa.String(length=50), nullable=True),
        sa.Column("building", sa.String(length=50), nullable=True),
        sa.Column("apartment", sa.String(length=50), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("full_address", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_addresses_id", "addresses", ["id"], unique=False)
    op.create_index("ix_addresses_city", "addresses", ["city"], unique=False)

    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("profile_type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kyc_status", sa.String(length=32), nullable=False, server_default="unverified"),
        sa.Column("kyc_provider", sa.String(length=100), nullable=True),
        sa.Column("kyc_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kyc_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_profiles_id", "profiles", ["id"], unique=False)
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=False)
    op.create_index("ix_profiles_profile_type", "profiles", ["profile_type"], unique=False)

    op.create_table(
        "individual_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("citizenship", sa.String(length=32), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("middle_name", sa.String(length=255), nullable=True),
        sa.Column("birth_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gender", sa.String(length=16), nullable=True),
        sa.Column("is_self_employed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("passport_series", sa.String(length=10), nullable=True),
        sa.Column("passport_number", sa.String(length=20), nullable=True),
        sa.Column("passport_issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("passport_issued_by", sa.String(length=500), nullable=True),
        sa.Column("passport_department_code", sa.String(length=20), nullable=True),
        sa.Column("registration_address_id", sa.Integer(), nullable=True),
        sa.Column("snils", sa.String(length=20), nullable=True),
        sa.Column("inn", sa.String(length=20), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("max_contact", sa.String(length=255), nullable=True),
        sa.Column("account_number", sa.String(length=32), nullable=True),
        sa.Column("correspondent_account", sa.String(length=32), nullable=True),
        sa.Column("bank_name", sa.String(length=255), nullable=True),
        sa.Column("bik", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registration_address_id"], ["addresses.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_individual_profiles_id", "individual_profiles", ["id"], unique=False)
    op.create_index("ix_individual_profiles_profile_id", "individual_profiles", ["profile_id"], unique=True)

    op.create_table(
        "legal_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=False),
        sa.Column("ogrn", sa.String(length=20), nullable=True),
        sa.Column("ogrn_assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inn", sa.String(length=20), nullable=True),
        sa.Column("okpo", sa.String(length=20), nullable=True),
        sa.Column("address_rf_id", sa.Integer(), nullable=True),
        sa.Column("representative_profile_id", sa.Integer(), nullable=True),
        sa.Column("representative_basis", sa.String(length=500), nullable=True),
        sa.Column("representative_position", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("max_contact", sa.String(length=255), nullable=True),
        sa.Column("account_number", sa.String(length=32), nullable=True),
        sa.Column("correspondent_account", sa.String(length=32), nullable=True),
        sa.Column("bank_name", sa.String(length=255), nullable=True),
        sa.Column("bik", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["address_rf_id"], ["addresses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["representative_profile_id"], ["individual_profiles.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_legal_profiles_id", "legal_profiles", ["id"], unique=False)
    op.create_index("ix_legal_profiles_profile_id", "legal_profiles", ["profile_id"], unique=True)

    op.create_table(
        "sole_proprietor_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("middle_name", sa.String(length=255), nullable=True),
        sa.Column("gender", sa.String(length=16), nullable=True),
        sa.Column("ogrnip", sa.String(length=20), nullable=True),
        sa.Column("inn", sa.String(length=20), nullable=True),
        sa.Column("okpo", sa.String(length=20), nullable=True),
        sa.Column("residence_address_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("max_contact", sa.String(length=255), nullable=True),
        sa.Column("account_number", sa.String(length=32), nullable=True),
        sa.Column("correspondent_account", sa.String(length=32), nullable=True),
        sa.Column("bank_name", sa.String(length=255), nullable=True),
        sa.Column("bik", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["residence_address_id"], ["addresses.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sole_proprietor_profiles_id", "sole_proprietor_profiles", ["id"], unique=False)
    op.create_index(
        "ix_sole_proprietor_profiles_profile_id", "sole_proprietor_profiles", ["profile_id"], unique=True
    )


def downgrade() -> None:
    """Drop profile and address tables."""
    op.drop_index("ix_sole_proprietor_profiles_profile_id", table_name="sole_proprietor_profiles")
    op.drop_index("ix_sole_proprietor_profiles_id", table_name="sole_proprietor_profiles")
    op.drop_table("sole_proprietor_profiles")

    op.drop_index("ix_legal_profiles_profile_id", table_name="legal_profiles")
    op.drop_index("ix_legal_profiles_id", table_name="legal_profiles")
    op.drop_table("legal_profiles")

    op.drop_index("ix_individual_profiles_profile_id", table_name="individual_profiles")
    op.drop_index("ix_individual_profiles_id", table_name="individual_profiles")
    op.drop_table("individual_profiles")

    op.drop_index("ix_profiles_profile_type", table_name="profiles")
    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_index("ix_profiles_id", table_name="profiles")
    op.drop_table("profiles")

    op.drop_index("ix_addresses_city", table_name="addresses")
    op.drop_index("ix_addresses_id", table_name="addresses")
    op.drop_table("addresses")

