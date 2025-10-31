"""add_notification_preferences_to_users

Revision ID: d26963b1a623
Revises: d32a5c094264
Create Date: 2025-10-31 09:37:02.739724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd26963b1a623'
down_revision: Union[str, Sequence[str], None] = 'd32a5c094264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле notification_preferences в таблицу users."""
    op.add_column(
        'users',
        sa.Column(
            'notification_preferences',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment='Настройки уведомлений пользователя (JSON: {type_code: {telegram: bool, inapp: bool}})'
        )
    )


def downgrade() -> None:
    """Удалить поле notification_preferences из таблицы users."""
    op.drop_column('users', 'notification_preferences')
