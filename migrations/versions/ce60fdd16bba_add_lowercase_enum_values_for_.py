"""add_lowercase_enum_values_for_notifications

Revision ID: ce60fdd16bba
Revises: f244dfa67bd3
Create Date: 2026-01-10 12:20:49.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce60fdd16bba'
down_revision: Union[str, Sequence[str], None] = 'ffaa1ceacd63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Этап 1: Добавить все недостающие lowercase значения в enum типы.
    
    PostgreSQL требует отдельные транзакции для ALTER TYPE и их использования в UPDATE.
    Эта миграция только добавляет значения, следующая миграция обновит данные.
    """
    
    # Маппинг значений для добавления
    notification_type_values = [
        'shift_reminder', 'shift_confirmed', 'shift_cancelled', 'shift_started', 
        'shift_completed', 'shift_did_not_start', 'contract_signed', 'contract_terminated',
        'contract_expiring', 'contract_updated', 'review_received', 'review_moderated',
        'appeal_submitted', 'appeal_decision', 'payment_due', 'payment_success',
        'payment_failed', 'subscription_expiring', 'subscription_expired',
        'usage_limit_warning', 'usage_limit_exceeded', 'welcome', 'password_reset',
        'account_suspended', 'account_activated', 'system_maintenance', 'feature_announcement'
    ]
    
    channel_values = ['email', 'sms', 'push', 'telegram', 'in_app', 'webhook', 'slack', 'discord']
    status_values = ['pending', 'sent', 'delivered', 'failed', 'read', 'cancelled']
    priority_values = ['low', 'normal', 'high', 'urgent']
    
    # Добавляем значения через DO блоки (каждый выполняется в отдельной транзакции благодаря Alembic)
    # Но PostgreSQL все равно требует коммит перед использованием - поэтому разделяем на две миграции
    
    # notificationtype
    for value in notification_type_values:
        op.execute(sa.text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = '{value}' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'notificationtype')
                ) THEN
                    ALTER TYPE notificationtype ADD VALUE '{value}';
                END IF;
            END $$;
        """))
    
    # notificationchannel
    for value in channel_values:
        op.execute(sa.text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = '{value}' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'notificationchannel')
                ) THEN
                    ALTER TYPE notificationchannel ADD VALUE '{value}';
                END IF;
            END $$;
        """))
    
    # notificationstatus
    for value in status_values:
        op.execute(sa.text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = '{value}' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'notificationstatus')
                ) THEN
                    ALTER TYPE notificationstatus ADD VALUE '{value}';
                END IF;
            END $$;
        """))
    
    # notificationpriority
    for value in priority_values:
        op.execute(sa.text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = '{value}' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'notificationpriority')
                ) THEN
                    ALTER TYPE notificationpriority ADD VALUE '{value}';
                END IF;
            END $$;
        """))


def downgrade() -> None:
    """
    Downgrade schema.
    
    ВНИМАНИЕ: PostgreSQL не поддерживает удаление значений из enum напрямую.
    Downgrade невозможен без пересоздания типов.
    """
    pass
