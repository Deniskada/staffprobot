"""Phase 1 MAX: messenger_accounts, profile_verifications, notification_targets.

Revision ID: 20260317_max_phase1
Revises: contract_expires_at_260223
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260317_max_phase1"
down_revision: Union[str, Sequence[str], None] = "contract_expires_at_260223"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. messenger_accounts: привязки TG/MAX/OAuth к user_id
    op.create_table(
        "messenger_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, comment="telegram | max | yandex_id | tinkoff_id"),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("chat_id", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_messenger_accounts_user_id", "messenger_accounts", ["user_id"])
    op.create_index("ix_messenger_accounts_provider_external", "messenger_accounts", ["provider", "external_user_id"], unique=True)
    op.create_index("ix_messenger_accounts_user_provider", "messenger_accounts", ["user_id", "provider"], unique=True)

    # 2. profile_verifications: задел под KYC
    op.create_table(
        "profile_verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("identity_key", sa.String(255), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_profile_verifications_profile_id", "profile_verifications", ["profile_id"])
    op.create_index("ix_profile_verifications_provider_identity", "profile_verifications", ["provider", "identity_key"], unique=True)
    op.create_index("ix_profile_verifications_profile_provider", "profile_verifications", ["profile_id", "provider"], unique=True)

    # 3. notification_targets: целевые чаты TG/MAX
    op.create_table(
        "notification_targets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_type", sa.String(32), nullable=False, comment="object | org_unit"),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("messenger", sa.String(32), nullable=False, comment="telegram | max"),
        sa.Column("target_type", sa.String(32), nullable=False, server_default="group"),
        sa.Column("target_chat_id", sa.String(255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_notification_targets_scope", "notification_targets", ["scope_type", "scope_id"])

    # 4. Backfill messenger_accounts из users.telegram_id
    op.execute("""
        INSERT INTO messenger_accounts (user_id, provider, external_user_id, chat_id, username, linked_at)
        SELECT id, 'telegram', telegram_id::text, telegram_id::text, username, created_at
        FROM users
        WHERE telegram_id IS NOT NULL
    """)

    # 5. Миграция TG report chat: objects → notification_targets
    op.execute("""
        INSERT INTO notification_targets (scope_type, scope_id, messenger, target_type, target_chat_id, is_enabled)
        SELECT 'object', id, 'telegram', 'group', telegram_report_chat_id, true
        FROM objects
        WHERE telegram_report_chat_id IS NOT NULL
    """)

    # 6. Миграция TG report chat: org_structure_units → notification_targets
    op.execute("""
        INSERT INTO notification_targets (scope_type, scope_id, messenger, target_type, target_chat_id, is_enabled)
        SELECT 'org_unit', id, 'telegram', 'group', telegram_report_chat_id, true
        FROM org_structure_units
        WHERE telegram_report_chat_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_table("notification_targets")
    op.drop_table("profile_verifications")
    op.drop_table("messenger_accounts")
