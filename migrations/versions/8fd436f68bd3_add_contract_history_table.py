"""add_contract_history_table

Revision ID: 8fd436f68bd3
Revises: a1b2c3d4e5f6
Create Date: 2026-01-15 11:42:18.538954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fd436f68bd3'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаем enum для типов изменений (если не существует)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contract_change_type AS ENUM ('created', 'updated', 'status_changed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Создаем таблицу contract_history
    op.create_table(
        'contract_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('change_type', sa.dialects.postgresql.ENUM('created', 'updated', 'status_changed', name='contract_change_type', create_type=False), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('new_value', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('change_metadata', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем индексы
    op.create_index('ix_contract_history_id', 'contract_history', ['id'])
    op.create_index('ix_contract_history_contract_id', 'contract_history', ['contract_id'])
    op.create_index('ix_contract_history_changed_by', 'contract_history', ['changed_by'])
    op.create_index('ix_contract_history_field_name', 'contract_history', ['field_name'])
    # Составные индексы с сортировкой через raw SQL
    op.execute("CREATE INDEX ix_contract_history_contract_id_changed_at ON contract_history (contract_id, changed_at DESC);")
    op.execute("CREATE INDEX ix_contract_history_contract_id_field_name_changed_at ON contract_history (contract_id, field_name, changed_at DESC);")
    op.execute("CREATE INDEX ix_contract_history_changed_by_changed_at ON contract_history (changed_by, changed_at DESC);")


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.execute("DROP INDEX IF EXISTS ix_contract_history_changed_by_changed_at;")
    op.execute("DROP INDEX IF EXISTS ix_contract_history_contract_id_field_name_changed_at;")
    op.execute("DROP INDEX IF EXISTS ix_contract_history_contract_id_changed_at;")
    op.drop_index('ix_contract_history_field_name', table_name='contract_history')
    op.drop_index('ix_contract_history_changed_by', table_name='contract_history')
    op.drop_index('ix_contract_history_contract_id', table_name='contract_history')
    op.drop_index('ix_contract_history_id', table_name='contract_history')
    
    # Удаляем таблицу
    op.drop_table('contract_history')
    
    # Удаляем enum
    op.execute("DROP TYPE contract_change_type;")
