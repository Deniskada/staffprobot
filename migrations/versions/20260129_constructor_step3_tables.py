"""Шаг 3 конструктора: таблица «Наименование работ» в schema и плейсхолдер во фрагменте.

Revision ID: step3_tables_260129
Revises: fix_step4_order_260129
Create Date: 2026-01-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "step3_tables_260129"
down_revision: Union[str, Sequence[str], None] = "fix_step4_order_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STEP3_SCHEMA = """{"info_block": "Перечень работ. При варианте «В договоре» можно заполнить таблицу работ.", "fields": [{"key": "works_where", "label": "Где указаны работы", "type": "radio"}], "options": [{"key": "in_contract", "label": "В договоре"}, {"key": "in_estimate", "label": "В смете"}], "tables": [{"id": "works", "label": "Наименование работ", "columns": [{"key": "name", "label": "Название работы", "type": "text"}, {"key": "qty", "label": "Кол-во", "type": "number"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "price", "label": "Стоимость", "type": "number"}]}]}"""

STEP3_SCHEMA_ORIG = """{"info_block": "Перечень работ.", "fields": [{"key": "works_where", "label": "Где указаны работы", "type": "radio"}], "options": [{"key": "in_contract", "label": "В договоре"}, {"key": "in_estimate", "label": "В смете"}]}"""

FRAGMENT_IN_CONTRACT = "<p><strong>3. Предмет договора</strong></p><p>Перечень работ указан в договоре.</p><p>{{ works }}</p>"
FRAGMENT_IN_CONTRACT_ORIG = "<p><strong>3. Предмет договора</strong></p><p>Перечень работ указан в договоре.</p>"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:schema AS jsonb) WHERE id = 3"), {"schema": STEP3_SCHEMA})
    conn.execute(sa.text("UPDATE constructor_fragments SET fragment_content = :content WHERE step_id = 3 AND option_key = 'in_contract'"), {"content": FRAGMENT_IN_CONTRACT})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:schema AS jsonb) WHERE id = 3"), {"schema": STEP3_SCHEMA_ORIG})
    conn.execute(sa.text("UPDATE constructor_fragments SET fragment_content = :content WHERE step_id = 3 AND option_key = 'in_contract'"), {"content": FRAGMENT_IN_CONTRACT_ORIG})
