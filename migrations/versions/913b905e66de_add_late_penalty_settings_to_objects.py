"""add_late_penalty_settings_to_objects

Revision ID: 913b905e66de
Revises: 5523c6f93307
Create Date: 2025-10-10 13:34:20.479609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '913b905e66de'
down_revision: Union[str, Sequence[str], None] = '5523c6f93307'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление настроек штрафов за опоздание в objects."""
    
    # Добавить флаг наследования
    op.add_column('objects', sa.Column('inherit_late_settings', sa.Boolean(), server_default='true', nullable=False))
    
    # Добавить допустимое время опозданий (в минутах)
    op.add_column('objects', sa.Column('late_threshold_minutes', sa.Integer(), nullable=True))
    
    # Добавить стоимость минуты штрафа (в рублях)
    op.add_column('objects', sa.Column('late_penalty_per_minute', sa.Numeric(10, 2), nullable=True))
    
    # Создать индексы
    op.create_index('idx_objects_inherit_late_settings', 'objects', ['inherit_late_settings'])
    
    # Комментарии
    op.execute("COMMENT ON COLUMN objects.inherit_late_settings IS 'Наследовать настройки штрафов от подразделения'")
    op.execute("COMMENT ON COLUMN objects.late_threshold_minutes IS 'Допустимое время опозданий в минутах (может быть отрицательным)'")
    op.execute("COMMENT ON COLUMN objects.late_penalty_per_minute IS 'Стоимость минуты штрафа за опоздание в рублях'")


def downgrade() -> None:
    """Откат: удаление настроек штрафов."""
    
    op.drop_index('idx_objects_inherit_late_settings', table_name='objects')
    op.drop_column('objects', 'late_penalty_per_minute')
    op.drop_column('objects', 'late_threshold_minutes')
    op.drop_column('objects', 'inherit_late_settings')
