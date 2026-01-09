"""add_shift_did_not_start_notification_type

Revision ID: f244dfa67bd3
Revises: f3faae39
Create Date: 2026-01-09 19:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f244dfa67bd3'
down_revision: Union[str, None] = 'ab7a492ca980'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить тип уведомления 'Смена не состоялась' в notification_types_meta."""
    op.execute("""
        INSERT INTO notification_types_meta 
        (type_code, title, description, category, default_priority, is_user_configurable, is_admin_only, available_channels, sort_order, is_active)
        VALUES
        ('shift_did_not_start', 'Смена не состоялась', 'Смена была запланирована сотрудником, но он не приступил к работе', 'shifts', 'high', true, false, '["telegram", "inapp"]', 15, true)
        ON CONFLICT (type_code) DO NOTHING
    """)


def downgrade() -> None:
    """Удалить тип уведомления 'Смена не состоялась'."""
    op.execute("""
        DELETE FROM notification_types_meta 
        WHERE type_code = 'shift_did_not_start'
    """)
