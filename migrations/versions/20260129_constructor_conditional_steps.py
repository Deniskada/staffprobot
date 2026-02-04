"""Условные шаги 7–10 (show_if от шага 6), шаг 8: conditionals + select «Срок».

Revision ID: cond_steps_260129
Revises: steps_6_19_260129
Create Date: 2026-01-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "cond_steps_260129"
down_revision: Union[str, Sequence[str], None] = "steps_6_19_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STEP7 = '''{"info_block": "Требования к качеству результата работ.", "show_if": {"step_slug": "extra", "field": "req_quality"}, "tables": [{"id": "quality", "label": "Требования к качеству", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}'''

STEP8 = '''{"info_block": "Гарантийный срок не менее 1 года по общему правилу.", "show_if": {"step_slug": "extra", "field": "req_warranty"}, "fields": [{"key": "warranty_type", "label": "Способ указания", "type": "radio"}, {"key": "warranty_date", "label": "Дата окончания", "type": "date"}, {"key": "warranty_count", "label": "Значение", "type": "number"}, {"key": "warranty_unit", "label": "Срок", "type": "select", "options": [{"key": "days", "label": "дней"}, {"key": "weeks", "label": "недель"}, {"key": "months", "label": "месяцев"}, {"key": "years", "label": "лет"}]}], "options": [{"key": "by_date", "label": "По календарной дате"}, {"key": "by_period", "label": "По истечении срока"}], "conditionals": [{"if_field": "_option", "eq": "by_date", "then_show_fields": ["warranty_date"]}, {"if_field": "_option", "eq": "by_period", "then_show_fields": ["warranty_count", "warranty_unit"]}]}'''

STEP9 = '''{"info_block": "Цели использования результата работ заказчиком.", "show_if": {"step_slug": "extra", "field": "req_goals"}, "tables": [{"id": "goals", "label": "Цели использования", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}'''

STEP10 = '''{"info_block": "Действия заказчика для обеспечения выполнения работ.", "show_if": {"step_slug": "extra", "field": "req_assistance"}, "tables": [{"id": "assistance", "label": "Содействие заказчика", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}'''

STEP8_ORIG = '''{"info_block": "Гарантийный срок не менее 1 года по общему правилу.", "fields": [{"key": "warranty_type", "label": "Способ указания", "type": "radio"}, {"key": "warranty_date", "label": "Дата окончания", "type": "date"}, {"key": "warranty_count", "label": "Количество", "type": "number"}, {"key": "warranty_unit", "label": "Единица (дней/недель/месяцев/лет)", "type": "text"}], "options": [{"key": "by_date", "label": "По календарной дате"}, {"key": "by_period", "label": "По истечении срока"}]}'''


def upgrade() -> None:
    conn = op.get_bind()
    for sid, schema in [(7, STEP7), (8, STEP8), (9, STEP9), (10, STEP10)]:
        conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = :id"), {"s": schema, "id": sid})


def downgrade() -> None:
    conn = op.get_bind()
    step7_orig = '''{"info_block": "Требования к качеству результата работ.", "tables": [{"id": "quality", "label": "Требования к качеству", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}'''
    step9_orig = '''{"info_block": "Цели использования результата работ заказчиком.", "tables": [{"id": "goals", "label": "Цели использования", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}'''
    step10_orig = '''{"info_block": "Действия заказчика для обеспечения выполнения работ.", "tables": [{"id": "assistance", "label": "Содействие заказчика", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}'''
    for sid, schema in [(7, step7_orig), (8, STEP8_ORIG), (9, step9_orig), (10, step10_orig)]:
        conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = :id"), {"s": schema, "id": sid})
