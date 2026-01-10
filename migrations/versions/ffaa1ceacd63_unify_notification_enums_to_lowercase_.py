"""unify_notification_enums_to_lowercase_values

Revision ID: ffaa1ceacd63
Revises: f244dfa67bd3
Create Date: 2026-01-10 10:59:14.639810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffaa1ceacd63'
down_revision: Union[str, Sequence[str], None] = 'f244dfa67bd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Этап 2: Унификация формата enum значений - обновление данных.
    
    Все enum поля теперь используют .value (lowercase строки).
    Первая миграция (ce60fdd16bba) уже добавила все lowercase значения в enum типы.
    Эта миграция обновляет существующие данные, заменяя uppercase на lowercase.
    """
    
    # Маппинг uppercase -> lowercase для всех enum типов
    notification_type_mappings = {
        'SHIFT_REMINDER': 'shift_reminder',
        'SHIFT_CONFIRMED': 'shift_confirmed',
        'SHIFT_CANCELLED': 'shift_cancelled',
        'SHIFT_STARTED': 'shift_started',
        'SHIFT_COMPLETED': 'shift_completed',
        'CONTRACT_SIGNED': 'contract_signed',
        'CONTRACT_TERMINATED': 'contract_terminated',
        'CONTRACT_EXPIRING': 'contract_expiring',
        'CONTRACT_UPDATED': 'contract_updated',
        'REVIEW_RECEIVED': 'review_received',
        'REVIEW_MODERATED': 'review_moderated',
        'APPEAL_SUBMITTED': 'appeal_submitted',
        'APPEAL_DECISION': 'appeal_decision',
        'PAYMENT_DUE': 'payment_due',
        'PAYMENT_SUCCESS': 'payment_success',
        'PAYMENT_FAILED': 'payment_failed',
        'SUBSCRIPTION_EXPIRING': 'subscription_expiring',
        'SUBSCRIPTION_EXPIRED': 'subscription_expired',
        'USAGE_LIMIT_WARNING': 'usage_limit_warning',
        'USAGE_LIMIT_EXCEEDED': 'usage_limit_exceeded',
        'WELCOME': 'welcome',
        'PASSWORD_RESET': 'password_reset',
        'ACCOUNT_SUSPENDED': 'account_suspended',
        'ACCOUNT_ACTIVATED': 'account_activated',
        'SYSTEM_MAINTENANCE': 'system_maintenance',
        'FEATURE_ANNOUNCEMENT': 'feature_announcement',
    }
    
    channel_mappings = {
        'EMAIL': 'email',
        'SMS': 'sms',
        'PUSH': 'push',
        'TELEGRAM': 'telegram',
        'IN_APP': 'in_app',
        'WEBHOOK': 'webhook',
        'SLACK': 'slack',
        'DISCORD': 'discord',
    }
    
    status_mappings = {
        'PENDING': 'pending',
        'SENT': 'sent',
        'DELIVERED': 'delivered',
        'FAILED': 'failed',
        'READ': 'read',
        'CANCELLED': 'cancelled',
    }
    
    priority_mappings = {
        'LOW': 'low',
        'NORMAL': 'normal',
        'HIGH': 'high',
        'URGENT': 'urgent',
    }
    
    # Обновить все записи в notifications, заменив uppercase на lowercase
    # Значения enum уже добавлены предыдущей миграцией (ce60fdd16bba)
    
    # Обновить type
    for uppercase, lowercase in notification_type_mappings.items():
        op.execute(sa.text("""
            UPDATE notifications 
            SET type = CAST(:lowercase AS notificationtype)
            WHERE type::text = :uppercase
        """).bindparams(lowercase=lowercase, uppercase=uppercase))
    
    # Обновить channel
    for uppercase, lowercase in channel_mappings.items():
        op.execute(sa.text("""
            UPDATE notifications 
            SET channel = CAST(:lowercase AS notificationchannel)
            WHERE channel::text = :uppercase
        """).bindparams(lowercase=lowercase, uppercase=uppercase))
    
    # Обновить status
    for uppercase, lowercase in status_mappings.items():
        op.execute(sa.text("""
            UPDATE notifications 
            SET status = CAST(:lowercase AS notificationstatus)
            WHERE status::text = :uppercase
        """).bindparams(lowercase=lowercase, uppercase=uppercase))
    
    # Обновить priority
    for uppercase, lowercase in priority_mappings.items():
        op.execute(sa.text("""
            UPDATE notifications 
            SET priority = CAST(:lowercase AS notificationpriority)
            WHERE priority::text = :uppercase
        """).bindparams(lowercase=lowercase, uppercase=uppercase))


def downgrade() -> None:
    """
    Downgrade schema.
    
    ВНИМАНИЕ: PostgreSQL не поддерживает удаление значений из enum напрямую.
    Также нельзя откатить UPDATE без резервной копии данных.
    Downgrade невозможен без пересоздания типов и восстановления данных из бэкапа.
    """
    pass
