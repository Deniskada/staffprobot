"""add employee_holiday_greeting notification type

Revision ID: 20260227_holiday_greeting
Revises: 20260227_employee_birthday
Create Date: 2026-02-27
"""
from typing import Sequence, Union
from alembic import op


revision: str = '20260227_holiday_greeting'
down_revision: Union[str, Sequence[str], None] = '20260227_employee_birthday'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO notification_types_meta
            (type_code, title, description, category, default_priority,
             is_user_configurable, is_admin_only, available_channels, sort_order, is_active)
        VALUES
            ('employee_holiday_greeting',
             'Поздравления с государственными праздниками',
             'Автоматические поздравления коллективу с праздниками РФ (Новый год, 8 Марта, '
             'День Победы и др.) — текст генерируется ИИ и отправляется в TG-группы объектов',
             'employees',
             'normal',
             true,
             false,
             '["telegram"]',
             51,
             true)
        ON CONFLICT (type_code) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM notification_types_meta WHERE type_code = 'employee_holiday_greeting';"
    )
