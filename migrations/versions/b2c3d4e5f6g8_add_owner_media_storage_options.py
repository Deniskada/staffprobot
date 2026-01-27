"""owner_media_storage_options + secure_media_storage (restruct1 Phase 1.5)

Revision ID: b2c3d4e5f6g8
Revises: a1b2c3d4e5f7
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6g8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "owner_media_storage_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("context", sa.String(length=30), nullable=False),
        sa.Column("storage", sa.String(length=20), nullable=False, server_default="telegram"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "context", name="uq_owner_media_storage_owner_context"),
    )
    op.create_index(
        "ix_owner_media_storage_options_owner_id",
        "owner_media_storage_options",
        ["owner_id"],
    )

    op.execute(
        sa.text("""
            INSERT INTO system_features (key, name, description, sort_order, menu_items, form_elements, is_active, usage_count)
            SELECT
                'secure_media_storage',
                'Использовать защищённое хранилище файлов',
                'Object Storage (S3/Selectel) для медиа: задачи, отмены, инциденты, договоры. Настройки «что и где» хранить.',
                11,
                '[]'::json,
                '[]'::json,
                true,
                0
            WHERE NOT EXISTS (SELECT 1 FROM system_features WHERE key = 'secure_media_storage')
        """)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_features WHERE key = 'secure_media_storage'"))
    op.drop_index("ix_owner_media_storage_options_owner_id", table_name="owner_media_storage_options")
    op.drop_table("owner_media_storage_options")
