"""owner profile theme/language/industry and industry terms

Revision ID: 20260325_owner_profile_theme
Revises: 20260317_messenger_accounts_profile_verif_notification_targets
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_owner_profile_theme"
down_revision = "20260317_max_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "owner_profiles",
        sa.Column("theme", sa.String(length=20), nullable=False, server_default="light"),
    )
    op.add_column(
        "owner_profiles",
        sa.Column("language", sa.String(length=10), nullable=False, server_default="ru"),
    )
    op.add_column(
        "owner_profiles",
        sa.Column("industry", sa.String(length=50), nullable=False, server_default="grocery"),
    )

    op.create_table(
        "industry_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("industry", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="ru"),
        sa.Column("term_key", sa.String(length=64), nullable=False),
        sa.Column("term_value", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("industry", "language", "term_key", name="uq_industry_terms"),
    )
    op.create_index(op.f("ix_industry_terms_id"), "industry_terms", ["id"], unique=False)
    op.create_index(op.f("ix_industry_terms_industry"), "industry_terms", ["industry"], unique=False)
    op.create_index(op.f("ix_industry_terms_language"), "industry_terms", ["language"], unique=False)
    op.create_index(op.f("ix_industry_terms_term_key"), "industry_terms", ["term_key"], unique=False)

    terms = [
        ("grocery", "ru", "object_singular", "Магазин"),
        ("grocery", "ru", "object_plural", "Магазины"),
        ("florist", "ru", "object_singular", "Салон"),
        ("florist", "ru", "object_plural", "Салоны"),
        ("pickup_point", "ru", "object_singular", "ПВЗ"),
        ("pickup_point", "ru", "object_plural", "ПВЗ"),
    ]
    for industry, language, term_key, term_value in terms:
        op.execute(
            sa.text(
                """
                INSERT INTO industry_terms (industry, language, term_key, term_value, source, is_active)
                VALUES (:industry, :language, :term_key, :term_value, 'seed', true)
                ON CONFLICT (industry, language, term_key) DO NOTHING
                """
            ).bindparams(
                industry=industry,
                language=language,
                term_key=term_key,
                term_value=term_value,
            )
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_industry_terms_term_key"), table_name="industry_terms")
    op.drop_index(op.f("ix_industry_terms_language"), table_name="industry_terms")
    op.drop_index(op.f("ix_industry_terms_industry"), table_name="industry_terms")
    op.drop_index(op.f("ix_industry_terms_id"), table_name="industry_terms")
    op.drop_table("industry_terms")
    op.drop_column("owner_profiles", "industry")
    op.drop_column("owner_profiles", "language")
    op.drop_column("owner_profiles", "theme")
