"""Add notification_templates table for custom templates

Revision ID: 3a9c09063654
Revises: 21bdf8e9a3c7
Create Date: 2025-10-13 21:39:59.309150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a9c09063654'
down_revision: Union[str, Sequence[str], None] = '21bdf8e9a3c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создание таблицы notification_templates для хранения кастомных шаблонов уведомлений
    # Используем существующие ENUM типы notificationtype и notificationchannel
    op.create_table('notification_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('template_key', sa.String(length=100), nullable=False, comment="Уникальный ключ шаблона (например: 'shift_reminder')"),
    sa.Column('type', postgresql.ENUM('SHIFT_REMINDER', 'SHIFT_CONFIRMED', 'SHIFT_CANCELLED', 'SHIFT_STARTED', 'SHIFT_COMPLETED', 'CONTRACT_SIGNED', 'CONTRACT_TERMINATED', 'CONTRACT_EXPIRING', 'CONTRACT_UPDATED', 'REVIEW_RECEIVED', 'REVIEW_MODERATED', 'APPEAL_SUBMITTED', 'APPEAL_DECISION', 'PAYMENT_DUE', 'PAYMENT_SUCCESS', 'PAYMENT_FAILED', 'SUBSCRIPTION_EXPIRING', 'SUBSCRIPTION_EXPIRED', 'USAGE_LIMIT_WARNING', 'USAGE_LIMIT_EXCEEDED', 'WELCOME', 'PASSWORD_RESET', 'ACCOUNT_SUSPENDED', 'ACCOUNT_ACTIVATED', 'SYSTEM_MAINTENANCE', 'FEATURE_ANNOUNCEMENT', name='notificationtype', create_type=False), nullable=False, comment='Тип уведомления'),
    sa.Column('channel', postgresql.ENUM('EMAIL', 'SMS', 'PUSH', 'TELEGRAM', 'IN_APP', 'WEBHOOK', 'SLACK', 'DISCORD', name='notificationchannel', create_type=False), nullable=True, comment='Канал доставки (если null - для всех каналов)'),
    sa.Column('name', sa.String(length=200), nullable=False, comment='Название шаблона'),
    sa.Column('description', sa.Text(), nullable=True, comment='Описание шаблона'),
    sa.Column('subject_template', sa.String(length=500), nullable=True, comment='Шаблон заголовка (с переменными $variable)'),
    sa.Column('plain_template', sa.Text(), nullable=False, comment='Текстовый шаблон (Plain Text с переменными $variable)'),
    sa.Column('html_template', sa.Text(), nullable=True, comment='HTML шаблон (с переменными $variable)'),
    sa.Column('variables', sa.Text(), nullable=True, comment='JSON список доступных переменных'),
    sa.Column('is_active', sa.Boolean(), nullable=True, comment='Активен ли шаблон'),
    sa.Column('is_default', sa.Boolean(), nullable=True, comment='Является ли дефолтным (из статических шаблонов)'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Дата создания'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='Дата обновления'),
    sa.Column('created_by', sa.Integer(), nullable=True, comment='ID пользователя, создавшего шаблон'),
    sa.Column('updated_by', sa.Integer(), nullable=True, comment='ID пользователя, обновившего шаблон'),
    sa.Column('version', sa.Integer(), nullable=True, comment='Версия шаблона'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_templates_id'), 'notification_templates', ['id'], unique=False)
    op.create_index(op.f('ix_notification_templates_is_active'), 'notification_templates', ['is_active'], unique=False)
    op.create_index(op.f('ix_notification_templates_template_key'), 'notification_templates', ['template_key'], unique=True)
    op.create_index(op.f('ix_notification_templates_type'), 'notification_templates', ['type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаление таблицы notification_templates
    op.drop_index(op.f('ix_notification_templates_type'), table_name='notification_templates')
    op.drop_index(op.f('ix_notification_templates_template_key'), table_name='notification_templates')
    op.drop_index(op.f('ix_notification_templates_is_active'), table_name='notification_templates')
    op.drop_index(op.f('ix_notification_templates_id'), table_name='notification_templates')
    op.drop_table('notification_templates')
