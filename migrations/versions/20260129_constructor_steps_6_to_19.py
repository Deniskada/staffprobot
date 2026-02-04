"""Расширение flow «Договор подряда»: шаги 6–19 по wf_konstr_shablonov, обновление шага 3.

Revision ID: steps_6_19_260129
Revises: step3_tables_260129
Create Date: 2026-01-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "steps_6_19_260129"
down_revision: Union[str, Sequence[str], None] = "step3_tables_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Шаг 3: добавить опцию «В ТЗ» и чекбокс «Разрешить привлекать субподряд»
    step3 = '{"info_block": "Перечень работ. При «В договоре» — таблица работ. Разрешение привлекать третьих лиц.", "fields": [{"key": "works_where", "label": "Где указаны работы", "type": "radio"}, {"key": "allow_subcontract", "label": "Разрешить подрядчику привлекать третьих лиц", "type": "checkbox"}], "options": [{"key": "in_contract", "label": "В договоре"}, {"key": "in_estimate", "label": "В смете"}, {"key": "in_tz", "label": "В техническом задании"}], "tables": [{"id": "works", "label": "Наименование работ", "columns": [{"key": "name", "label": "Название работы", "type": "text"}, {"key": "qty", "label": "Кол-во", "type": "number"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "price", "label": "Стоимость", "type": "number"}]}]}'
    conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 3"), {"s": step3})

    conn.execute(sa.text("""
        INSERT INTO constructor_fragments (id, step_id, option_key, fragment_content) VALUES
        (70, 3, 'in_tz', '<p><strong>3. Предмет договора</strong></p><p>Перечень работ указан в техническом задании.</p>')
        ON CONFLICT (id) DO NOTHING
    """))

    # Шаги 6–19
    steps = [
        (6, 1, 6, "Дополнительные требования", "extra", '{"info_block": "Отметьте, что включать в договор.", "fields": [{"key": "req_quality", "label": "Требования к качеству работ", "type": "checkbox"}, {"key": "req_warranty", "label": "Гарантийные сроки", "type": "checkbox"}, {"key": "req_goals", "label": "Цели использования результата", "type": "checkbox"}, {"key": "req_assistance", "label": "Содействие заказчика", "type": "checkbox"}]}', False),
        (7, 1, 7, "Условия о качестве", "quality", '{"info_block": "Требования к качеству результата работ.", "tables": [{"id": "quality", "label": "Требования к качеству", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}', False),
        (8, 1, 8, "Гарантийный срок", "warranty", '{"info_block": "Гарантийный срок не менее 1 года по общему правилу.", "fields": [{"key": "warranty_type", "label": "Способ указания", "type": "radio"}, {"key": "warranty_date", "label": "Дата окончания", "type": "date"}, {"key": "warranty_count", "label": "Количество", "type": "number"}, {"key": "warranty_unit", "label": "Единица (дней/недель/месяцев/лет)", "type": "text"}], "options": [{"key": "by_date", "label": "По календарной дате"}, {"key": "by_period", "label": "По истечении срока"}]}', False),
        (9, 1, 9, "Цели использования", "goals", '{"info_block": "Цели использования результата работ заказчиком.", "tables": [{"id": "goals", "label": "Цели использования", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}', False),
        (10, 1, 10, "Содействие заказчика", "assistance", '{"info_block": "Действия заказчика для обеспечения выполнения работ.", "tables": [{"id": "assistance", "label": "Содействие заказчика", "columns": [{"key": "desc", "label": "Описание", "type": "text"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "criterion", "label": "Критерий достижения", "type": "text"}]}]}', False),
        (11, 1, 11, "Стоимость работ", "cost", '{"info_block": "Стоимость включает издержки и вознаграждение подрядчика.", "fields": [{"key": "ndfl", "label": "НДФЛ", "type": "radio"}, {"key": "cost_by_estimate", "label": "Стоимость определяется сметой", "type": "checkbox"}, {"key": "cost_approximate", "label": "Стоимость указана приблизительно", "type": "checkbox"}], "options": [{"key": "13", "label": "13%"}, {"key": "30", "label": "30%"}]}', False),
        (12, 1, 12, "Порядок оплаты", "payment", '{"info_block": "Способы оплаты: предоплата, по факту, отсрочка. Наличные между ЮЛ — лимит 100 000 ₽.", "fields": [{"key": "pay_prepay", "label": "Предоплата", "type": "checkbox"}, {"key": "pay_fact", "label": "Оплата по факту", "type": "checkbox"}, {"key": "pay_defer", "label": "Отсрочка оплаты", "type": "checkbox"}, {"key": "amount_type", "label": "Способ указания сумм (руб/%)", "type": "text"}, {"key": "pay_form", "label": "Форма расчётов", "type": "text"}, {"key": "payment_date", "label": "Дата платежа", "type": "text"}]}', False),
        (13, 1, 13, "Предоплата", "payment_prepay", '{"info_block": "Оплата до завершения работ.", "fields": [{"key": "prepay_type", "label": "Срок", "type": "radio"}, {"key": "prepay_amount", "label": "Сумма (₽)", "type": "number"}, {"key": "prepay_date", "label": "Дата платежа", "type": "date"}, {"key": "prepay_days", "label": "Дней от заключения/начала работ", "type": "number"}], "options": [{"key": "exact_date", "label": "Точная дата"}, {"key": "from_contract", "label": "С момента заключения"}, {"key": "from_work", "label": "С момента начала работ"}]}', False),
        (14, 1, 14, "Оплата по факту", "payment_fact", '{"info_block": "Оплата при передаче результата.", "fields": [{"key": "fact_amount", "label": "Сумма (₽)", "type": "number"}]}', False),
        (15, 1, 15, "Отсрочка оплаты", "payment_defer", '{"info_block": "Оплата спустя время после приёмки.", "fields": [{"key": "defer_amount", "label": "Сумма (₽)", "type": "number"}, {"key": "defer_days", "label": "Срок отсрочки (дней)", "type": "number"}, {"key": "defer_reward", "label": "Вознаграждение за отсрочку", "type": "checkbox"}, {"key": "defer_reward_pct", "label": "Размер вознаграждения (%)", "type": "number"}]}', False),
        (16, 1, 16, "Принятие результата работ", "acceptance", '{"info_block": "Срок приёмки и последствия просрочки приёмки.", "fields": [{"key": "acceptance_days", "label": "Срок приёмки (дней)", "type": "number"}, {"key": "overdue_acceptance_days", "label": "Просрочка приёмки — работы приняты (дней)", "type": "number"}]}', False),
        (17, 1, 17, "Ответственность сторон", "liability", '{"info_block": "Неустойки. Оптимально 0,1–1%.", "fields": [{"key": "liab_contractor", "label": "Ответственность подрядчика", "type": "checkbox"}, {"key": "liab_contractor_pct", "label": "Неустойка подрядчика (%)", "type": "number"}, {"key": "liab_increased", "label": "Повышенная ответственность за просрочку", "type": "checkbox"}, {"key": "liab_increased_days", "label": "Дней до повышенной ответственности", "type": "number"}, {"key": "liab_customer", "label": "Ответственность заказчика", "type": "checkbox"}, {"key": "liab_customer_pct", "label": "Неустойка заказчика (%)", "type": "number"}]}', False),
        (18, 1, 18, "Разрешение споров", "disputes", '{"info_block": "Претензионный порядок и подсудность.", "fields": [{"key": "court_place", "label": "Подсудность", "type": "radio"}, {"key": "claim_required", "label": "Претензионный порядок обязателен", "type": "checkbox"}, {"key": "claim_days", "label": "Срок ответа на претензию (раб. дн.)", "type": "number"}], "options": [{"key": "defendant", "label": "По месту ответчика"}, {"key": "plaintiff", "label": "По месту истца"}, {"key": "customer", "label": "По месту заказчика"}, {"key": "contractor", "label": "По месту подрядчика"}]}', False),
        (19, 1, 19, "Дополнительные условия", "misc", '{"info_block": "Форс-мажор и конфиденциальность.", "fields": [{"key": "force_majeure", "label": "Условие о форс-мажоре", "type": "checkbox"}, {"key": "confidentiality", "label": "Условие о конфиденциальности", "type": "checkbox"}]}', False),
    ]
    for sid, fid, so, title, slug, schema_json, req in steps:
        conn.execute(sa.text("""
            INSERT INTO constructor_steps (id, flow_id, sort_order, title, slug, schema, request_at_conclusion)
            VALUES (:sid, :fid, :so, :title, :slug, CAST(:schema AS jsonb), :req)
            ON CONFLICT (id) DO NOTHING
        """), {"sid": sid, "fid": fid, "so": so, "title": title, "slug": slug, "schema": schema_json, "req": req})

    # Фрагменты для шагов 6–19 (option_key null — один фрагмент на шаг)
    frags = [
        (7, 6, None, "<p><strong>6. Дополнительные требования</strong></p><p>Требования к качеству, гарантия, цели использования, содействие заказчика — по отметкам сторон.</p>"),
        (8, 7, None, "<p><strong>6.1. Условия о качестве</strong></p><p>{{ quality }}</p>"),
        (9, 8, None, "<p><strong>6.2. Гарантийный срок</strong></p><p>Гарантия: {{ _option }} {{ warranty_date }} {{ warranty_count }} {{ warranty_unit }}.</p>"),
        (10, 9, None, "<p><strong>6.3. Цели использования</strong></p><p>{{ goals }}</p>"),
        (11, 10, None, "<p><strong>6.4. Содействие заказчика</strong></p><p>{{ assistance }}</p>"),
        (12, 11, None, "<p><strong>7. Стоимость работ</strong></p><p>НДФЛ {{ _option }}%. Стоимость по смете/приблизительно — по выбору.</p>"),
        (13, 12, None, "<p><strong>8. Порядок оплаты</strong></p><p>Предоплата, по факту, отсрочка. {{ amount_type }}, {{ pay_form }}, {{ payment_date }}.</p>"),
        (14, 13, None, "<p><strong>8.1. Предоплата</strong></p><p>{{ prepay_amount }} ₽, {{ _option }} {{ prepay_date }} {{ prepay_days }}.</p>"),
        (15, 14, None, "<p><strong>8.2. Оплата по факту</strong></p><p>{{ fact_amount }} ₽.</p>"),
        (16, 15, None, "<p><strong>8.3. Отсрочка оплаты</strong></p><p>{{ defer_amount }} ₽, {{ defer_days }} дн. {{ defer_reward }} {{ defer_reward_pct }}%.</p>"),
        (17, 16, None, "<p><strong>9. Принятие результата</strong></p><p>Срок приёмки {{ acceptance_days }} дн., при просрочке приёмки — {{ overdue_acceptance_days }} дн.</p>"),
        (18, 17, None, "<p><strong>10. Ответственность</strong></p><p>Подрядчик: {{ liab_contractor }} {{ liab_contractor_pct }}%. Повышенная: {{ liab_increased }} {{ liab_increased_days }} дн. Заказчик: {{ liab_customer }} {{ liab_customer_pct }}%.</p>"),
        (19, 18, None, "<p><strong>11. Разрешение споров</strong></p><p>Претензия {{ claim_required }} {{ claim_days }} дн. Подсудность: {{ _option }}.</p>"),
        (20, 19, None, "<p><strong>12. Доп. условия</strong></p><p>Форс-мажор: {{ force_majeure }}. Конфиденциальность: {{ confidentiality }}.</p>"),
    ]
    for frag_id, step_id, opt_key, content in frags:
        conn.execute(sa.text("""
            INSERT INTO constructor_fragments (id, step_id, option_key, fragment_content)
            VALUES (:fid, :step_id, :opt_key, :content)
            ON CONFLICT (id) DO NOTHING
        """), {"fid": frag_id, "step_id": step_id, "opt_key": opt_key, "content": content})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM constructor_fragments WHERE step_id IN (6,7,8,9,10,11,12,13,14,15,16,17,18,19)"))
    conn.execute(sa.text("DELETE FROM constructor_fragments WHERE id = 70"))
    conn.execute(sa.text("DELETE FROM constructor_steps WHERE id BETWEEN 6 AND 19"))
    # Восстановить шаг 3 до версии с tables (без in_tz и allow_subcontract)
    step3 = '{"info_block": "Перечень работ. При варианте «В договоре» можно заполнить таблицу работ.", "fields": [{"key": "works_where", "label": "Где указаны работы", "type": "radio"}], "options": [{"key": "in_contract", "label": "В договоре"}, {"key": "in_estimate", "label": "В смете"}], "tables": [{"id": "works", "label": "Наименование работ", "columns": [{"key": "name", "label": "Название работы", "type": "text"}, {"key": "qty", "label": "Кол-во", "type": "number"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "price", "label": "Стоимость", "type": "number"}]}]}'
    conn.execute(sa.text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 3"), {"s": step3})
