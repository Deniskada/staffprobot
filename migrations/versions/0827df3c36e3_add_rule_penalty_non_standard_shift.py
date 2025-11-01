"""add_rule_penalty_non_standard_shift

Revision ID: 0827df3c36e3
Revises: ea3ab2aa3487
Create Date: 2025-11-01 20:50:51.671015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0827df3c36e3'
down_revision: Union[str, Sequence[str], None] = 'ea3ab2aa3487'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление автоправила "Штраф за опоздание на вечернюю смену (или в нерабочее время)"."""
    import json
    
    # Создаём системное правило (owner_id = NULL)
    condition_json = json.dumps({
        'description': 'Штраф за опоздания на смены, начало которых не совпадает со временем начала работы объекта',
        'planned_start_matches_opening_time': False
    }, ensure_ascii=False)
    
    action_json = json.dumps({
        'type': 'fine',
        'code': 'penalty_non_standard_shift',
        'label': 'Штраф за опоздание на вечернюю смену (или в нерабочее время)',
        'description': 'Начисляется штраф за опоздание на смены, запланированные не в время начала работы объекта'
    }, ensure_ascii=False)
    
    # Экранируем кавычки для SQL
    condition_json_escaped = condition_json.replace("'", "''")
    action_json_escaped = action_json.replace("'", "''")
    
    # Проверяем существование правила
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM rules WHERE code = 'penalty_non_standard_shift'"))
    existing = result.fetchone()
    
    if existing:
        # Обновляем существующее правило
        op.execute(f"""
            UPDATE rules 
            SET name = 'Штраф за опоздание на вечернюю смену (или в нерабочее время)',
                condition_json = '{condition_json_escaped}',
                action_json = '{action_json_escaped}',
                updated_at = NOW()
            WHERE code = 'penalty_non_standard_shift'
        """)
    else:
        # Создаём новое правило
        op.execute(f"""
            INSERT INTO rules (owner_id, code, name, is_active, priority, scope, condition_json, action_json, created_at, updated_at)
            VALUES (
                NULL,
                'penalty_non_standard_shift',
                'Штраф за опоздание на вечернюю смену (или в нерабочее время)',
                true,
                50,
                'late',
                '{condition_json_escaped}',
                '{action_json_escaped}',
                NOW(),
                NOW()
            )
        """)


def downgrade() -> None:
    """Откат: удаление автоправила."""
    op.execute("DELETE FROM rules WHERE code = 'penalty_non_standard_shift'")
