"""add_task_notification_types

Revision ID: c887be040290
Revises: 069c779926e9
Create Date: 2025-10-31 11:50:11.000000

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c887be040290'
down_revision: Union[str, Sequence[str], None] = '069c779926e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить типы уведомлений по задачам."""
    
    # 1. Добавляем новые значения в enum
    op.execute("""
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'task_assigned';
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'task_completed';
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'task_overdue';
    """)
    
    # 2. Добавляем записи в notification_types_meta
    task_types = [
        {
            'type_code': 'task_assigned',
            'title': 'Назначена задача',
            'description': 'Уведомление когда вам назначена новая задача',
            'category': 'tasks',
            'default_priority': 'normal',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 71
        },
        {
            'type_code': 'task_completed',
            'title': 'Задача выполнена',
            'description': 'Уведомление когда задача выполнена',
            'category': 'tasks',
            'default_priority': 'low',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 72
        },
        {
            'type_code': 'task_overdue',
            'title': 'Задача просрочена',
            'description': 'Уведомление когда задача не выполнена в срок',
            'category': 'tasks',
            'default_priority': 'high',
            'is_user_configurable': True,
            'is_admin_only': False,
            'available_channels': ['telegram', 'in_app'],
            'sort_order': 73
        }
    ]
    
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
    
    for task_type in task_types:
        op.execute(
            f"""
            INSERT INTO notification_types_meta 
            (type_code, title, description, category, default_priority, is_user_configurable, is_admin_only, available_channels, sort_order, is_active)
            VALUES (
                '{task_type['type_code']}',
                '{task_type['title']}',
                '{task_type['description']}',
                '{task_type['category']}',
                '{task_type['default_priority']}',
                {task_type['is_user_configurable']},
                {task_type['is_admin_only']},
                '{json.dumps(task_type['available_channels'])}'::json,
                {task_type['sort_order']},
                true
            )
            ON CONFLICT (type_code) DO NOTHING
            """
        )


def downgrade() -> None:
    """Удалить типы уведомлений по задачам."""
    op.execute("""
        DELETE FROM notification_types_meta 
        WHERE type_code IN ('task_assigned', 'task_completed', 'task_overdue')
    """)
    # Enum значения нельзя удалить в PostgreSQL
