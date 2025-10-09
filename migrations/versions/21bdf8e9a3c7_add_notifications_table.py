"""add notifications table

Revision ID: 21bdf8e9a3c7
Revises: abcd1234
Create Date: 2025-10-09 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '21bdf8e9a3c7'
down_revision: Union[str, Sequence[str], None] = 'abcd1234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Расширяем существующие enum типы новыми значениями
    # NotificationType - добавляем типы для смен, договоров, отзывов, системных уведомлений
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SHIFT_REMINDER'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SHIFT_CONFIRMED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SHIFT_CANCELLED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SHIFT_STARTED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SHIFT_COMPLETED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'CONTRACT_SIGNED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'CONTRACT_TERMINATED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'CONTRACT_EXPIRING'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'CONTRACT_UPDATED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'REVIEW_RECEIVED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'REVIEW_MODERATED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'APPEAL_SUBMITTED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'APPEAL_DECISION'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'WELCOME'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'PASSWORD_RESET'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'ACCOUNT_SUSPENDED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'ACCOUNT_ACTIVATED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SYSTEM_MAINTENANCE'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'FEATURE_ANNOUNCEMENT'")
    
    # NotificationChannel - добавляем PUSH, SLACK, DISCORD
    op.execute("ALTER TYPE notificationchannel ADD VALUE IF NOT EXISTS 'PUSH'")
    op.execute("ALTER TYPE notificationchannel ADD VALUE IF NOT EXISTS 'SLACK'")
    op.execute("ALTER TYPE notificationchannel ADD VALUE IF NOT EXISTS 'DISCORD'")
    
    # NotificationStatus - добавляем CANCELLED
    op.execute("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'CANCELLED'")
    
    # Создаем новый enum тип NotificationPriority
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationpriority AS ENUM ('LOW', 'NORMAL', 'HIGH', 'URGENT');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Создаем таблицу notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', postgresql.ENUM(name='notificationtype', create_type=False), nullable=False),
        sa.Column('channel', postgresql.ENUM(name='notificationchannel', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM(name='notificationstatus', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('priority', postgresql.ENUM(name='notificationpriority', create_type=False), nullable=False, server_default='NORMAL'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем индексы для оптимизации запросов
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_status', 'notifications', ['status'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('ix_notifications_scheduled_at', 'notifications', ['scheduled_at'])
    
    # Составной индекс для частого запроса (непрочитанные уведомления пользователя)
    op.create_index('ix_notifications_user_status', 'notifications', ['user_id', 'status'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index('ix_notifications_user_status', table_name='notifications')
    op.drop_index('ix_notifications_scheduled_at', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_status', table_name='notifications')
    op.drop_index('ix_notifications_type', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    
    # Удаляем таблицу
    op.drop_table('notifications')
    
    # Удаляем enum типы
    op.execute('DROP TYPE IF EXISTS notificationtype')
    op.execute('DROP TYPE IF EXISTS notificationchannel')
    op.execute('DROP TYPE IF EXISTS notificationstatus')
    op.execute('DROP TYPE IF EXISTS notificationpriority')

