"""update_shift_tasks_structure_to_objects

Обновление структуры shift_tasks с массива строк на массив объектов.

Revision ID: dcb9f508b8d3
Revises: 9cc315b1e50c
Create Date: 2025-10-10 07:43:24.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcb9f508b8d3'
down_revision: Union[str, Sequence[str], None] = '9cc315b1e50c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Преобразование shift_tasks из массива строк в массив объектов."""
    
    # Обновить существующие записи
    # Проверяем, что shift_tasks это массив и первый элемент - строка (не объект)
    op.execute("""
        UPDATE objects
        SET shift_tasks = (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'text', task_text,
                    'is_mandatory', true,
                    'deduction_amount', 100.0
                )
            )
            FROM jsonb_array_elements_text(shift_tasks) AS task_text
        )
        WHERE shift_tasks IS NOT NULL 
        AND jsonb_typeof(shift_tasks) = 'array'
        AND (
            SELECT COUNT(*) 
            FROM jsonb_array_elements(shift_tasks) AS elem 
            WHERE jsonb_typeof(elem) = 'string'
        ) > 0;
    """)
    
    # Обновить комментарий
    op.execute("""
        COMMENT ON COLUMN objects.shift_tasks IS 
        'Задачи на смену в формате JSON: [{"text": "Уборка", "is_mandatory": true, "deduction_amount": 100.0}]'
    """)


def downgrade() -> None:
    """Откат: преобразование обратно в массив строк."""
    
    # Вернуть к массиву строк
    op.execute("""
        UPDATE objects
        SET shift_tasks = (
            SELECT jsonb_agg(task->>'text')
            FROM jsonb_array_elements(shift_tasks) AS task
        )
        WHERE shift_tasks IS NOT NULL 
        AND jsonb_typeof(shift_tasks) = 'array'
        AND jsonb_array_length(shift_tasks) > 0
        AND jsonb_typeof(shift_tasks->0) = 'object';
    """)
    
    # Вернуть комментарий
    op.execute("""
        COMMENT ON COLUMN objects.shift_tasks IS 
        'Задачи на смену в формате JSON массива строк'
    """)
