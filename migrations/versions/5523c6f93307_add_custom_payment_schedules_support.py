"""add_custom_payment_schedules_support

Revision ID: 5523c6f93307
Revises: 810af3219ad5
Create Date: 2025-10-10 11:10:55.744672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5523c6f93307'
down_revision: Union[str, Sequence[str], None] = '810af3219ad5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление поддержки кастомных графиков выплат."""
    
    # Добавить owner_id (владелец кастомного графика)
    op.add_column('payment_schedules', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_payment_schedules_owner_id',
        'payment_schedules', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Добавить object_id (привязка к конкретному объекту)
    op.add_column('payment_schedules', sa.Column('object_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_payment_schedules_object_id',
        'payment_schedules', 'objects',
        ['object_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Добавить is_custom (флаг кастомного графика)
    op.add_column('payment_schedules', sa.Column('is_custom', sa.Boolean(), server_default='false', nullable=False))
    
    # Создать индексы
    op.create_index('idx_payment_schedules_owner_id', 'payment_schedules', ['owner_id'])
    op.create_index('idx_payment_schedules_object_id', 'payment_schedules', ['object_id'])
    op.create_index('idx_payment_schedules_is_custom', 'payment_schedules', ['is_custom'])
    
    # Комментарии
    op.execute("COMMENT ON COLUMN payment_schedules.owner_id IS 'Владелец кастомного графика (NULL для системных)'")
    op.execute("COMMENT ON COLUMN payment_schedules.object_id IS 'Привязка к конкретному объекту (NULL для общих)'")
    op.execute("COMMENT ON COLUMN payment_schedules.is_custom IS 'Кастомный график (созданный пользователем)'")


def downgrade() -> None:
    """Откат: удаление полей для кастомных графиков."""
    
    # Удалить индексы
    op.drop_index('idx_payment_schedules_is_custom', table_name='payment_schedules')
    op.drop_index('idx_payment_schedules_object_id', table_name='payment_schedules')
    op.drop_index('idx_payment_schedules_owner_id', table_name='payment_schedules')
    
    # Удалить foreign keys
    op.drop_constraint('fk_payment_schedules_object_id', 'payment_schedules', type_='foreignkey')
    op.drop_constraint('fk_payment_schedules_owner_id', 'payment_schedules', type_='foreignkey')
    
    # Удалить колонки
    op.drop_column('payment_schedules', 'is_custom')
    op.drop_column('payment_schedules', 'object_id')
    op.drop_column('payment_schedules', 'owner_id')
