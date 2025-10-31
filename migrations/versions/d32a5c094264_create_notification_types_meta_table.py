"""create_notification_types_meta_table

Revision ID: d32a5c094264
Revises: 20251029_incidents_ext
Create Date: 2025-10-31 08:21:40.933211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd32a5c094264'
down_revision: Union[str, Sequence[str], None] = '20251029_incidents_ext'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создание таблицы notification_types_meta
    op.create_table(
        'notification_types_meta',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type_code', sa.String(length=50), nullable=False, comment='Код типа (соответствует NotificationType enum)'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='Название типа на русском (для UI)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Подробное описание для пользователей'),
        sa.Column('category', sa.String(length=50), nullable=False, comment='Категория: shifts, contracts, reviews, payments, system, tasks, applications'),
        sa.Column('default_priority', sa.String(length=20), nullable=False, server_default='normal', comment='Приоритет по умолчанию: low, normal, high, critical'),
        sa.Column('is_user_configurable', sa.Boolean(), nullable=False, server_default='false', comment='Показывать ли в настройках владельца/пользователя'),
        sa.Column('is_admin_only', sa.Boolean(), nullable=False, server_default='false', comment='Только для администраторов (не показывать владельцу)'),
        sa.Column('available_channels', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]', comment="Список доступных каналов: ['telegram', 'inapp', 'email']"),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='Порядок отображения в UI'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Активен ли тип уведомления'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание индексов
    op.create_index('ix_notification_types_meta_type_code', 'notification_types_meta', ['type_code'], unique=True)
    op.create_index('ix_notification_types_meta_category', 'notification_types_meta', ['category'])
    op.create_index('ix_notification_types_meta_is_user_configurable', 'notification_types_meta', ['is_user_configurable'])
    op.create_index('ix_notification_types_meta_is_active', 'notification_types_meta', ['is_active'])
    
    # Заполнение таблицы всеми 26 типами уведомлений
    op.execute("""
        INSERT INTO notification_types_meta 
        (type_code, title, description, category, default_priority, is_user_configurable, is_admin_only, available_channels, sort_order, is_active)
        VALUES
        -- Смены (15 типов доступны для настройки владельцем)
        ('shift_reminder', 'Напоминание о смене', 'Уведомление о начале смены за 1 час', 'shifts', 'high', true, false, '["telegram", "inapp"]', 10, true),
        ('shift_confirmed', 'Смена подтверждена', 'Уведомление о подтверждении смены сотрудником', 'shifts', 'normal', true, false, '["telegram", "inapp"]', 11, true),
        ('shift_cancelled', 'Смена отменена', 'Уведомление об отмене смены', 'shifts', 'high', true, false, '["telegram", "inapp"]', 12, true),
        ('shift_started', 'Смена началась', 'Уведомление о фактическом начале смены', 'shifts', 'normal', true, false, '["telegram", "inapp"]', 13, true),
        ('shift_completed', 'Смена завершена', 'Уведомление о завершении смены', 'shifts', 'normal', true, false, '["telegram", "inapp"]', 14, true),
        
        -- Объекты
        ('object_opened', 'Объект открылся', 'Уведомление об открытии объекта вовремя', 'objects', 'normal', true, false, '["telegram", "inapp"]', 15, true),
        ('object_closed', 'Объект закрылся', 'Уведомление о закрытии объекта', 'objects', 'normal', true, false, '["telegram", "inapp"]', 16, true),
        ('object_late_opening', 'Объект открылся с опозданием', 'Уведомление об открытии объекта с опозданием', 'objects', 'high', true, false, '["telegram", "inapp"]', 17, true),
        ('object_no_shifts_today', 'Нет смен на объекте', 'Уведомление об отсутствии смен на объекте сегодня', 'objects', 'high', true, false, '["telegram", "inapp"]', 18, true),
        ('object_early_closing', 'Объект закрылся раньше', 'Уведомление о раннем закрытии объекта', 'objects', 'high', true, false, '["telegram", "inapp"]', 19, true),
        
        -- Договоры
        ('contract_signed', 'Договор подписан', 'Уведомление о подписании нового договора', 'contracts', 'high', true, false, '["telegram", "inapp"]', 20, true),
        ('contract_terminated', 'Договор расторгнут', 'Уведомление о расторжении договора', 'contracts', 'high', true, false, '["telegram", "inapp"]', 21, true),
        ('contract_expiring', 'Договор истекает', 'Уведомление об истечении срока договора', 'contracts', 'high', true, false, '["telegram", "inapp"]', 22, true),
        ('contract_updated', 'Договор обновлён', 'Уведомление об изменении условий договора', 'contracts', 'normal', true, false, '["telegram", "inapp"]', 23, true),
        
        -- Отзывы
        ('review_received', 'Получен отзыв', 'Уведомление о новом отзыве', 'reviews', 'normal', true, false, '["telegram", "inapp"]', 30, true),
        ('review_moderated', 'Отзыв промодерирован', 'Уведомление о результатах модерации отзыва', 'reviews', 'normal', true, false, '["telegram", "inapp"]', 31, true),
        ('appeal_submitted', 'Подано обжалование', 'Уведомление о подаче обжалования отзыва', 'reviews', 'high', true, false, '["telegram", "inapp"]', 32, true),
        ('appeal_decision', 'Решение по обжалованию', 'Уведомление о решении по обжалованию отзыва', 'reviews', 'high', true, false, '["telegram", "inapp"]', 33, true),
        
        -- Платежи
        ('payment_due', 'Предстоящий платёж', 'Уведомление о предстоящем платеже за подписку', 'payments', 'high', true, false, '["telegram", "inapp", "email"]', 40, true),
        ('payment_success', 'Платёж успешен', 'Уведомление об успешном платеже', 'payments', 'normal', true, false, '["telegram", "inapp"]', 41, true),
        ('payment_failed', 'Платёж не прошёл', 'Уведомление о неудачной попытке платежа', 'payments', 'critical', true, false, '["telegram", "inapp", "email"]', 42, true),
        ('subscription_expiring', 'Подписка истекает', 'Уведомление об истечении подписки', 'payments', 'high', true, false, '["telegram", "inapp", "email"]', 43, true),
        ('subscription_expired', 'Подписка истекла', 'Уведомление об истечении подписки (блокировка доступа)', 'payments', 'critical', true, false, '["telegram", "inapp", "email"]', 44, true),
        ('usage_limit_warning', 'Предупреждение о лимите', 'Уведомление о приближении к лимиту использования', 'payments', 'high', false, false, '["telegram", "inapp"]', 45, true),
        ('usage_limit_exceeded', 'Лимит превышен', 'Уведомление о превышении лимита использования', 'payments', 'critical', false, false, '["telegram", "inapp", "email"]', 46, true),
        
        -- Системные (только для администраторов)
        ('welcome', 'Приветствие', 'Приветственное сообщение новому пользователю', 'system', 'normal', false, true, '["telegram", "inapp"]', 50, true),
        ('password_reset', 'Сброс пароля', 'Уведомление о запросе сброса пароля', 'system', 'high', false, true, '["telegram", "email"]', 51, true),
        ('account_suspended', 'Аккаунт заблокирован', 'Уведомление о блокировке аккаунта', 'system', 'critical', false, true, '["telegram", "inapp", "email"]', 52, true),
        ('account_activated', 'Аккаунт активирован', 'Уведомление об активации аккаунта', 'system', 'normal', false, true, '["telegram", "inapp"]', 53, true),
        ('system_maintenance', 'Системное обслуживание', 'Уведомление о плановых технических работах', 'system', 'high', false, true, '["telegram", "inapp", "email"]', 54, true),
        ('feature_announcement', 'Анонс функции', 'Уведомление о новой функции системы', 'system', 'low', false, true, '["telegram", "inapp"]', 55, true);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notification_types_meta_is_active', table_name='notification_types_meta')
    op.drop_index('ix_notification_types_meta_is_user_configurable', table_name='notification_types_meta')
    op.drop_index('ix_notification_types_meta_category', table_name='notification_types_meta')
    op.drop_index('ix_notification_types_meta_type_code', table_name='notification_types_meta')
    op.drop_table('notification_types_meta')
