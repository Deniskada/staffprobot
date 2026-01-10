"""add_incident_notification_types

Revision ID: a1b2c3d4e5f6
Revises: ce60fdd16bba
Create Date: 2026-01-10 17:30:00.000000

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ce60fdd16bba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить типы уведомлений об инцидентах в enum и мета-таблицу."""
    
    # Добавляем значения в enum notificationtype
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'incident_created'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'incident_resolved'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'incident_rejected'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'incident_cancelled'")
    
    # Типы уведомлений об инцидентах
    incident_types = [
        {
            'type_code': 'incident_created',
            'title': 'Инцидент создан',
            'description': 'Уведомление о создании нового инцидента',
            'category': 'incidents',
            'default_priority': 'high',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 70
        },
        {
            'type_code': 'incident_resolved',
            'title': 'Инцидент решён',
            'description': 'Уведомление о решении инцидента',
            'category': 'incidents',
            'default_priority': 'normal',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 71
        },
        {
            'type_code': 'incident_rejected',
            'title': 'Инцидент отклонён',
            'description': 'Уведомление об отклонении инцидента',
            'category': 'incidents',
            'default_priority': 'normal',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 72
        },
        {
            'type_code': 'incident_cancelled',
            'title': 'Инцидент отменён',
            'description': 'Уведомление об отмене инцидента',
            'category': 'incidents',
            'default_priority': 'normal',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 73
        }
    ]
    
    # Вставляем типы в мета-таблицу
    from sqlalchemy import table, column, String, Boolean, Integer
    from sqlalchemy.dialects.postgresql import JSON
    
    notification_types_meta = table(
        'notification_types_meta',
        column('type_code', String),
        column('title', String),
        column('description', String),
        column('category', String),
        column('default_priority', String),
        column('is_user_configurable', Boolean),
        column('is_admin_only', Boolean),
        column('available_channels', JSON),
        column('sort_order', Integer),
        column('is_active', Boolean)
    )
    
    for incident_type in incident_types:
        op.execute(
            f"""
            INSERT INTO notification_types_meta 
            (type_code, title, description, category, default_priority, is_user_configurable, is_admin_only, available_channels, sort_order, is_active)
            VALUES (
                '{incident_type['type_code']}',
                '{incident_type['title']}',
                '{incident_type['description']}',
                '{incident_type['category']}',
                '{incident_type['default_priority']}',
                {incident_type['is_user_configurable']},
                {incident_type['is_admin_only']},
                '{json.dumps(incident_type['available_channels'])}'::json,
                {incident_type['sort_order']},
                true
            )
            ON CONFLICT (type_code) DO NOTHING
            """
        )


def downgrade() -> None:
    """Удалить типы уведомлений об инцидентах."""
    op.execute("""
        DELETE FROM notification_types_meta 
        WHERE type_code IN (
            'incident_created', 
            'incident_resolved', 
            'incident_rejected', 
            'incident_cancelled'
        )
    """)
    # Примечание: удаление значений из enum в PostgreSQL невозможно без пересоздания типа
