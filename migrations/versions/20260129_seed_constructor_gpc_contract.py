"""Сид: тип договора подряда и flow «Договор подряда» с шагами и фрагментами.

Revision ID: seed_constructor_gpc_260129
Revises: constructor_flows_260129
Create Date: 2026-01-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "seed_constructor_gpc_260129"
down_revision: Union[str, Sequence[str], None] = "constructor_flows_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # contract_types
    conn.execute(sa.text("INSERT INTO contract_types (id, code, label) VALUES (1, 'gpc_contract', 'Договор подряда (ГПХ)') ON CONFLICT (code) DO NOTHING"))
    conn.execute(sa.text("INSERT INTO contract_types (id, code, label) VALUES (2, 'services', 'Договор оказания услуг') ON CONFLICT (code) DO NOTHING"))
    conn.execute(sa.text("INSERT INTO contract_types (id, code, label) VALUES (3, 'employment', 'Трудовой договор') ON CONFLICT (code) DO NOTHING"))
    # constructor_flows (id=1)
    conn.execute(sa.text("INSERT INTO constructor_flows (id, contract_type_id, name, version, is_active, source) VALUES (1, 1, 'Договор подряда', '1.0', true, 'manual') ON CONFLICT (id) DO NOTHING"))
    # constructor_steps
    steps_data = [
        (1, 1, 1, "Заказчик", "customer", '{"info_block": "Укажите тип заказчика.", "fields": [{"key": "customer_type", "label": "Тип заказчика", "type": "radio", "required": true}], "options": [{"key": "ip", "label": "ИП"}, {"key": "legal", "label": "ЮЛ"}, {"key": "individual", "label": "ФЛ"}]}', False),
        (2, 1, 2, "Подрядчик", "contractor", '{"info_block": "Тип подрядчика.", "fields": [{"key": "contractor_type", "label": "Тип подрядчика", "type": "radio", "required": true}], "options": [{"key": "ip", "label": "ИП"}, {"key": "legal", "label": "ЮЛ"}, {"key": "individual", "label": "ФЛ"}]}', False),
        (3, 1, 3, "Объект договора", "object", '{"info_block": "Перечень работ.", "fields": [{"key": "works_where", "label": "Где указаны работы", "type": "radio"}], "options": [{"key": "in_contract", "label": "В договоре"}, {"key": "in_estimate", "label": "В смете"}]}', False),
        (4, 1, 4, "Сроки и материалы", "terms", '{"info_block": "Сроки и поставщик материалов.", "fields": [{"key": "work_start", "label": "Начало работ", "type": "date"}, {"key": "work_end", "label": "Окончание работ", "type": "date"}, {"key": "supplier", "label": "Поставщик материалов", "type": "radio"}], "options": [{"key": "contractor", "label": "Подрядчик"}, {"key": "customer", "label": "Заказчик"}]}', False),
        (5, 1, 5, "Сведения о договоре", "contract_info", '{"info_block": "Номер, место, дата — при заключении.", "fields": [{"key": "contract_number", "label": "Номер договора", "type": "text"}, {"key": "sign_place", "label": "Место подписания", "type": "text"}, {"key": "sign_date", "label": "Дата подписания", "type": "date"}]}', True),
    ]
    for sid, flow_id, sort_order, title, slug, schema_json, req in steps_data:
        conn.execute(
            sa.text("INSERT INTO constructor_steps (id, flow_id, sort_order, title, slug, schema, request_at_conclusion) VALUES (:sid, :flow_id, :sort_order, :title, :slug, CAST(:schema_json AS jsonb), :req) ON CONFLICT (id) DO NOTHING"),
            {"sid": sid, "flow_id": flow_id, "sort_order": sort_order, "title": title, "slug": slug, "schema_json": schema_json, "req": req},
        )
    # constructor_fragments
    frags = [
        (1, 1, None, "<p><strong>1. Заказчик</strong></p><p>Заказчик по договору подряда (ИП / ЮЛ / ФЛ). Данные подставляются при заключении.</p>"),
        (2, 2, None, "<p><strong>2. Подрядчик</strong></p><p>Подрядчик — исполнитель работ. Реквизиты подставляются при заключении из данных сотрудника.</p>"),
        (3, 3, "in_contract", "<p><strong>3. Предмет договора</strong></p><p>Перечень работ указан в договоре.</p>"),
        (4, 3, "in_estimate", "<p><strong>3. Предмет договора</strong></p><p>Перечень работ указан в смете.</p>"),
        (5, 4, None, "<p><strong>4. Сроки выполнения работ</strong></p><p>Сроки — существенные условия. Начало и окончание указываются в договоре или при заключении.</p>"),
        (6, 5, None, "<p><strong>5. Сведения о договоре</strong></p><p>Номер, место и дата подписания: {{ contract_number }}, {{ sign_place }}, {{ sign_date }}.</p>"),
    ]
    for fid, step_id, opt_key, content in frags:
        conn.execute(
            sa.text("INSERT INTO constructor_fragments (id, step_id, option_key, fragment_content) VALUES (:fid, :step_id, :opt_key, :content) ON CONFLICT (id) DO NOTHING"),
            {"fid": fid, "step_id": step_id, "opt_key": opt_key, "content": content},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM constructor_fragments WHERE step_id IN (SELECT id FROM constructor_steps WHERE flow_id = 1)"))
    conn.execute(sa.text("DELETE FROM constructor_steps WHERE flow_id = 1"))
    conn.execute(sa.text("DELETE FROM constructor_flows WHERE id = 1"))
    conn.execute(sa.text("DELETE FROM contract_types WHERE id IN (1, 2, 3)"))
