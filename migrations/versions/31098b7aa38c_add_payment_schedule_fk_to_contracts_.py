"""add_payment_schedule_fk_to_contracts_objects

Добавление связи с payment_schedules в contracts и objects.

Revision ID: 31098b7aa38c
Revises: 5d3d105cbbe1
Create Date: 2025-10-09 15:01:14.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31098b7aa38c'
down_revision: Union[str, Sequence[str], None] = '5d3d105cbbe1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление payment_schedule_id в contracts и objects."""
    
    # === CONTRACTS ===
    
    # Добавить payment_schedule_id
    op.add_column('contracts', 
        sa.Column('payment_schedule_id', sa.Integer(), nullable=True)
    )
    
    # Создать FK
    op.create_foreign_key(
        'fk_contracts_payment_schedule_id', 
        'contracts', 'payment_schedules',
        ['payment_schedule_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создать индекс
    op.create_index('idx_contracts_payment_schedule_id', 'contracts', ['payment_schedule_id'])
    
    # Комментарий
    op.execute(
        "COMMENT ON COLUMN contracts.payment_schedule_id IS "
        "'График выплат для сотрудника'"
    )
    
    # === OBJECTS ===
    
    # Добавить payment_schedule_id
    op.add_column('objects', 
        sa.Column('payment_schedule_id', sa.Integer(), nullable=True)
    )
    
    # Создать FK
    op.create_foreign_key(
        'fk_objects_payment_schedule_id', 
        'objects', 'payment_schedules',
        ['payment_schedule_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создать индекс
    op.create_index('idx_objects_payment_schedule_id', 'objects', ['payment_schedule_id'])
    
    # Комментарий
    op.execute(
        "COMMENT ON COLUMN objects.payment_schedule_id IS "
        "'График выплат для объекта (переопределяет org_unit)'"
    )


def downgrade() -> None:
    """Откат: удаление payment_schedule_id."""
    
    # OBJECTS
    op.drop_index('idx_objects_payment_schedule_id', table_name='objects')
    op.drop_constraint('fk_objects_payment_schedule_id', 'objects', type_='foreignkey')
    op.drop_column('objects', 'payment_schedule_id')
    
    # CONTRACTS
    op.drop_index('idx_contracts_payment_schedule_id', table_name='contracts')
    op.drop_constraint('fk_contracts_payment_schedule_id', 'contracts', type_='foreignkey')
    op.drop_column('contracts', 'payment_schedule_id')
