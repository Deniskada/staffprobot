"""add_object_notification_types_to_meta

Revision ID: 069c779926e9
Revises: 809625543f59
Create Date: 2025-10-31 11:43:39.594046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '069c779926e9'
down_revision: Union[str, Sequence[str], None] = '809625543f59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить типы уведомлений по объектам в notification_types_meta."""
    
    # Типы уведомлений по объектам
    object_types = [
        {
            'type_code': 'object_opened',
            'title': 'Объект открылся',
            'description': 'Уведомление когда объект открылся вовремя',
            'category': 'objects',
            'default_priority': 'normal',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 61
        },
        {
            'type_code': 'object_closed',
            'title': 'Объект закрылся',
            'description': 'Уведомление когда объект закрылся',
            'category': 'objects',
            'default_priority': 'normal',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 62
        },
        {
            'type_code': 'object_late_opening',
            'title': 'Объект открылся с опозданием',
            'description': 'Уведомление когда объект открылся позже запланированного времени',
            'category': 'objects',
            'default_priority': 'high',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 63
        },
        {
            'type_code': 'object_no_shifts_today',
            'title': 'Нет смен на объекте',
            'description': 'Уведомление когда на объекте нет запланированных смен на сегодня',
            'category': 'objects',
            'default_priority': 'high',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 64
        },
        {
            'type_code': 'object_early_closing',
            'title': 'Объект закрылся раньше',
            'description': 'Уведомление когда объект закрылся раньше запланированного времени',
            'category': 'objects',
            'default_priority': 'high',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 65
        }
    ]
    
    # Вставляем типы
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
    
    for obj_type in object_types:
        op.execute(
            notification_types_meta.insert().values(
                type_code=obj_type['type_code'],
                title=obj_type['title'],
                description=obj_type['description'],
                category=obj_type['category'],
                default_priority=obj_type['default_priority'],
                is_user_configurable=obj_type['is_user_configurable'],
                is_admin_only=obj_type['is_admin_only'],
                available_channels=obj_type['available_channels'],
                sort_order=obj_type['sort_order'],
                is_active=True
            ).on_conflict_do_nothing(index_elements=['type_code'])
        )


def downgrade() -> None:
    """Удалить типы уведомлений по объектам."""
    op.execute("""
        DELETE FROM notification_types_meta 
        WHERE type_code IN (
            'object_opened', 
            'object_closed', 
            'object_late_opening', 
            'object_no_shifts_today', 
            'object_early_closing'
        )
    """)
