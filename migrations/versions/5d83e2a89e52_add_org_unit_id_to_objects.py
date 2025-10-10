"""add_org_unit_id_to_objects

Revision ID: 5d83e2a89e52
Revises: 03a82e1b8667
Create Date: 2025-10-10 16:17:23.483099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d83e2a89e52'
down_revision: Union[str, Sequence[str], None] = '03a82e1b8667'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление связи объектов с подразделениями."""
    
    # Добавить поле org_unit_id в objects
    op.add_column('objects', sa.Column('org_unit_id', sa.Integer(), nullable=True))
    
    # Создать внешний ключ
    op.create_foreign_key(
        'fk_objects_org_unit_id',
        'objects', 'org_structure_units',
        ['org_unit_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создать индекс
    op.create_index('idx_objects_org_unit_id', 'objects', ['org_unit_id'])
    
    # Комментарий
    op.execute("COMMENT ON COLUMN objects.org_unit_id IS 'Подразделение, к которому относится объект'")
    
    # Установить значение по умолчанию для существующих объектов
    # Для каждого объекта найти "Основное подразделение" его владельца
    op.execute("""
        UPDATE objects o
        SET org_unit_id = (
            SELECT osu.id 
            FROM org_structure_units osu
            WHERE osu.owner_id = o.owner_id 
              AND osu.parent_id IS NULL 
              AND osu.name = 'Основное подразделение'
            LIMIT 1
        )
        WHERE org_unit_id IS NULL
    """)


def downgrade() -> None:
    """Откат: удаление связи объектов с подразделениями."""
    
    # Удалить индекс
    op.drop_index('idx_objects_org_unit_id', table_name='objects')
    
    # Удалить внешний ключ
    op.drop_constraint('fk_objects_org_unit_id', 'objects', type_='foreignkey')
    
    # Удалить столбец
    op.drop_column('objects', 'org_unit_id')
