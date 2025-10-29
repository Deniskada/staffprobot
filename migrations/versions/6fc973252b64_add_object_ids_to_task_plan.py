"""add_object_ids_to_task_plan

Revision ID: 6fc973252b64
Revises: 244eacdc1fef
Create Date: 2025-10-27 11:51:58.459995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fc973252b64'
down_revision: Union[str, Sequence[str], None] = '244eacdc1fef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле object_ids для множественного выбора объектов
    op.add_column('task_plans_v2', sa.Column('object_ids', sa.JSON(), nullable=True))
    
    # Мигрируем данные: если есть object_id, создаём массив [object_id]
    op.execute("""
        UPDATE task_plans_v2 
        SET object_ids = jsonb_build_array(object_id)
        WHERE object_id IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_plans_v2', 'object_ids')
