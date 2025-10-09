"""add_payment_system_fk_to_contracts_objects

Добавление связи с payment_systems в contracts и objects.

Revision ID: 97d3b944c0b9
Revises: b6c9fd9375d0
Create Date: 2025-10-09 14:12:12.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97d3b944c0b9'
down_revision: Union[str, Sequence[str], None] = 'b6c9fd9375d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление payment_system_id в contracts и objects."""
    
    # === CONTRACTS ===
    
    # Добавить payment_system_id
    op.add_column('contracts', 
        sa.Column('payment_system_id', sa.Integer(), nullable=True)
    )
    
    # Создать FK
    op.create_foreign_key(
        'fk_contracts_payment_system_id', 
        'contracts', 'payment_systems',
        ['payment_system_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создать индекс
    op.create_index('idx_contracts_payment_system_id', 'contracts', ['payment_system_id'])
    
    # Комментарий
    op.execute(
        "COMMENT ON COLUMN contracts.payment_system_id IS "
        "'Система оплаты труда (по умолчанию simple_hourly)'"
    )
    
    # Назначить simple_hourly всем существующим договорам
    op.execute("""
        UPDATE contracts 
        SET payment_system_id = (SELECT id FROM payment_systems WHERE code = 'simple_hourly')
        WHERE payment_system_id IS NULL
    """)
    
    # === OBJECTS ===
    
    # Добавить payment_system_id
    op.add_column('objects', 
        sa.Column('payment_system_id', sa.Integer(), nullable=True)
    )
    
    # Создать FK
    op.create_foreign_key(
        'fk_objects_payment_system_id', 
        'objects', 'payment_systems',
        ['payment_system_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создать индекс
    op.create_index('idx_objects_payment_system_id', 'objects', ['payment_system_id'])
    
    # Комментарий
    op.execute(
        "COMMENT ON COLUMN objects.payment_system_id IS "
        "'Система оплаты для объекта (переопределяет org_unit)'"
    )


def downgrade() -> None:
    """Откат: удаление payment_system_id."""
    
    # OBJECTS
    op.drop_index('idx_objects_payment_system_id', table_name='objects')
    op.drop_constraint('fk_objects_payment_system_id', 'objects', type_='foreignkey')
    op.drop_column('objects', 'payment_system_id')
    
    # CONTRACTS
    op.drop_index('idx_contracts_payment_system_id', table_name='contracts')
    op.drop_constraint('fk_contracts_payment_system_id', 'contracts', type_='foreignkey')
    op.drop_column('contracts', 'payment_system_id')
