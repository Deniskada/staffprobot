"""Normalize users.roles to jsonb with default [] and NOT NULL

Revision ID: 20250917_roles_jsonb_fix
Revises: 0444a3097a83
Create Date: 2025-09-17 12:55:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250917_roles_jsonb_fix'
down_revision: Union[str, Sequence[str], None] = '0444a3097a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure column exists before altering (no-op if already there)
    conn = op.get_bind()
    has_roles = conn.execute(sa.text(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name='users' AND column_name='roles'
        """
    )).fetchone()

    if not has_roles:
        op.add_column('users', sa.Column('roles', sa.JSON(), nullable=True))

    # Drop default to allow type change
    op.execute("ALTER TABLE users ALTER COLUMN roles DROP DEFAULT")

    # Convert to jsonb using to_jsonb if stored as text[] or json text
    op.execute("ALTER TABLE users ALTER COLUMN roles TYPE jsonb USING to_jsonb(roles)")

    # Set default [] and backfill NULLs
    op.execute("ALTER TABLE users ALTER COLUMN roles SET DEFAULT '[]'::jsonb")
    op.execute("UPDATE users SET roles='[]'::jsonb WHERE roles IS NULL")
    op.execute("ALTER TABLE users ALTER COLUMN roles SET NOT NULL")


def downgrade() -> None:
    # Revert to JSON (not jsonb), keep data
    op.execute("ALTER TABLE users ALTER COLUMN roles DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN roles TYPE json USING roles::json")
    op.execute("ALTER TABLE users ALTER COLUMN roles SET DEFAULT '[]'")
    # Keep NOT NULL to preserve constraints

