"""create_org_structure_units_table

Revision ID: 03a82e1b8667
Revises: 913b905e66de
Create Date: 2025-10-10 16:13:43.474670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03a82e1b8667'
down_revision: Union[str, Sequence[str], None] = '913b905e66de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы org_structure_units и seed-данных."""
    
    # Создать таблицу org_structure_units
    op.create_table(
        'org_structure_units',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('payment_system_id', sa.Integer(), nullable=True),
        sa.Column('payment_schedule_id', sa.Integer(), nullable=True),
        sa.Column('inherit_late_settings', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('late_threshold_minutes', sa.Integer(), nullable=True),
        sa.Column('late_penalty_per_minute', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['org_structure_units.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_system_id'], ['payment_systems.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_schedule_id'], ['payment_schedules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создать индексы
    op.create_index('idx_org_units_owner_id', 'org_structure_units', ['owner_id'])
    op.create_index('idx_org_units_parent_id', 'org_structure_units', ['parent_id'])
    op.create_index('idx_org_units_level', 'org_structure_units', ['level'])
    op.create_index('idx_org_units_is_active', 'org_structure_units', ['is_active'])
    
    # Комментарии к таблице и столбцам
    op.execute("COMMENT ON TABLE org_structure_units IS 'Организационная структура (подразделения)'")
    op.execute("COMMENT ON COLUMN org_structure_units.parent_id IS 'Родительское подразделение (для древовидной структуры)'")
    op.execute("COMMENT ON COLUMN org_structure_units.level IS 'Уровень в иерархии (0 - корень)'")
    op.execute("COMMENT ON COLUMN org_structure_units.inherit_late_settings IS 'Наследовать настройки штрафов от родителя'")
    op.execute("COMMENT ON COLUMN org_structure_units.late_threshold_minutes IS 'Допустимое опоздание в минутах'")
    op.execute("COMMENT ON COLUMN org_structure_units.late_penalty_per_minute IS 'Стоимость минуты штрафа в рублях'")
    
    # Seed-данные: создать "Основное подразделение" для всех существующих владельцев (role='owner')
    op.execute("""
        INSERT INTO org_structure_units (owner_id, parent_id, name, description, level, is_active, created_at, updated_at)
        SELECT 
            id, 
            NULL,
            'Основное подразделение',
            'Подразделение по умолчанию',
            0,
            true,
            now(),
            now()
        FROM users
        WHERE role = 'owner'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    """Откат: удаление таблицы org_structure_units."""
    
    # Удалить индексы
    op.drop_index('idx_org_units_is_active', table_name='org_structure_units')
    op.drop_index('idx_org_units_level', table_name='org_structure_units')
    op.drop_index('idx_org_units_parent_id', table_name='org_structure_units')
    op.drop_index('idx_org_units_owner_id', table_name='org_structure_units')
    
    # Удалить таблицу
    op.drop_table('org_structure_units')
