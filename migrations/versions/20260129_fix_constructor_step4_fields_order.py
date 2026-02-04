"""Порядок полей шага 4: supplier первым, чтобы options привязывались к нему.

Revision ID: fix_step4_order_260129
Revises: seed_constructor_gpc_260129
Create Date: 2026-01-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "fix_step4_order_260129"
down_revision: Union[str, Sequence[str], None] = "seed_constructor_gpc_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STEP4_SCHEMA = """{"info_block": "Сроки и поставщик материалов.", "fields": [{"key": "supplier", "label": "Поставщик материалов", "type": "radio"}, {"key": "work_start", "label": "Начало работ", "type": "date"}, {"key": "work_end", "label": "Окончание работ", "type": "date"}], "options": [{"key": "contractor", "label": "Подрядчик"}, {"key": "customer", "label": "Заказчик"}]}"""


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:schema AS jsonb) WHERE id = 4"), {"schema": STEP4_SCHEMA})


def downgrade() -> None:
    orig = """{"info_block": "Сроки и поставщик материалов.", "fields": [{"key": "work_start", "label": "Начало работ", "type": "date"}, {"key": "work_end", "label": "Окончание работ", "type": "date"}, {"key": "supplier", "label": "Поставщик материалов", "type": "radio"}], "options": [{"key": "contractor", "label": "Подрядчик"}, {"key": "customer", "label": "Заказчик"}]}"""
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:schema AS jsonb) WHERE id = 4"), {"schema": orig})
