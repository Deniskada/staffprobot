"""Фаза 3 конструктора: полные названия, conditionals, переименования, show_if.

Revision ID: phase3_260130
Revises: full_body_260129
Create Date: 2026-01-30
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "phase3_260130"
down_revision: Union[str, Sequence[str], None] = "full_body_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column(
        "contract_templates",
        sa.Column("constructor_values", sa.JSON(), nullable=True, comment="step_choices из мастера (profile_id и др.)"),
    )

    # Шаг 1: полные названия кнопок, profile_select для выбора профиля собственника
    s1 = '''{"info_block": "Укажите тип заказчика и выберите профиль для привязки в шаблон.", "fields": [{"key": "customer_type", "label": "Тип заказчика", "type": "radio", "required": true}, {"key": "customer_profile_id", "label": "Профиль заказчика", "type": "profile_select", "profile_source": "owner_organization"}], "options": [{"key": "ip", "label": "Индивидуальный предприниматель"}, {"key": "legal", "label": "Юридическое лицо"}, {"key": "individual", "label": "Физическое лицо"}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 1"), {"s": s1})

    # Шаг 2: полные названия, чекбокс Самозанятый (только при ФЛ)
    s2 = '''{"info_block": "Укажите тип подрядчика. Профиль выбирается при подписании.", "fields": [{"key": "contractor_type", "label": "Тип подрядчика", "type": "radio", "required": true}, {"key": "is_self_employed", "label": "Самозанятый", "type": "checkbox"}], "options": [{"key": "ip", "label": "Индивидуальный предприниматель"}, {"key": "legal", "label": "Юридическое лицо"}, {"key": "individual", "label": "Физическое лицо"}], "conditionals": [{"if_field": "_option", "eq": "individual", "then_show_fields": ["is_self_employed"]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 2"), {"s": s2})

    # Шаг 3: полные названия опций (таблица показывается только при in_contract — в UI)
    s3 = '''{"info_block": "Перечень работ. При «В договоре» — таблица работ.", "fields": [{"key": "works_where", "label": "Где указаны работы", "type": "radio"}, {"key": "allow_subcontract", "label": "Разрешить подрядчику привлекать третьих лиц", "type": "checkbox"}], "options": [{"key": "in_contract", "label": "В договоре"}, {"key": "in_estimate", "label": "В смете"}, {"key": "in_tz", "label": "В техническом задании"}], "tables": [{"id": "works", "label": "Наименование работ", "show_if_option": "in_contract", "columns": [{"key": "name", "label": "Название работы", "type": "text"}, {"key": "qty", "label": "Кол-во", "type": "number"}, {"key": "unit", "label": "Ед. изм.", "type": "text"}, {"key": "price", "label": "Стоимость", "type": "number"}]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 3"), {"s": s3})

    # Шаг 4: три варианта поставщика, conditionals для сроков и ответственности
    s4 = '''{"info_block": "Сроки и поставщик материалов.", "fields": [{"key": "supplier", "label": "Поставщик материалов", "type": "radio"}, {"key": "materials_days", "label": "Срок в днях передачи", "type": "number"}, {"key": "materials_late_resp", "label": "Установить ответственность за просрочку передачи", "type": "checkbox"}, {"key": "work_start", "label": "Начало работ", "type": "date"}, {"key": "work_end", "label": "Окончание работ", "type": "date"}], "options": [{"key": "contractor", "label": "Подрядчик предоставляет материалы и оборудование"}, {"key": "customer_partial", "label": "Заказчик предоставляет материалы, оборудование — подрядчик"}, {"key": "customer_full", "label": "Заказчик предоставляет материалы и оборудование"}], "conditionals": [{"if_field": "_option", "eq": "customer_partial", "then_show_fields": ["materials_days", "materials_late_resp"]}, {"if_field": "_option", "eq": "customer_full", "then_show_fields": ["materials_days", "materials_late_resp"]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 4"), {"s": s4})

    # Шаг 12: select вместо text для amount_type, pay_form, payment_date
    s12 = '''{"info_block": "Способы оплаты: предоплата, по факту, отсрочка. Наличные между ЮЛ — лимит 100 000 ₽.", "fields": [{"key": "pay_prepay", "label": "Предоплата", "type": "checkbox"}, {"key": "pay_fact", "label": "Оплата по факту", "type": "checkbox"}, {"key": "pay_defer", "label": "Отсрочка оплаты", "type": "checkbox"}, {"key": "amount_type", "label": "Способ указания сумм", "type": "select", "options": [{"key": "rub", "label": "Рубли"}, {"key": "pct", "label": "%"}]}, {"key": "pay_form", "label": "Форма расчётов", "type": "select", "options": [{"key": "cashless", "label": "Безналичный расчёт"}, {"key": "cash", "label": "Наличный расчёт"}]}, {"key": "payment_date", "label": "Дата совершения платежа", "type": "select", "options": [{"key": "credit_date", "label": "Дата зачисления денежных средств на расчётный счёт получателя"}, {"key": "order_date", "label": "Дата получения банком плательщика платёжного поручения о переводе денежных средств"}]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 12"), {"s": s12})

    # Шаг 13: show_if от шага 12 (pay_prepay), переименования, conditionals (prepay_date только при exact_date, prepay_days при from_contract/from_work)
    s13 = '''{"info_block": "Оплата до завершения работ.", "show_if": {"step_slug": "payment", "field": "pay_prepay"}, "fields": [{"key": "prepay_type", "label": "Срок", "type": "radio"}, {"key": "prepay_amount", "label": "Размер предоплаты в рублях", "type": "number"}, {"key": "prepay_date", "label": "Дата платежа", "type": "date"}, {"key": "prepay_days", "label": "Срок предоплаты в днях", "type": "number"}], "options": [{"key": "exact_date", "label": "Точная дата"}, {"key": "from_contract", "label": "С момента заключения Договора"}, {"key": "from_work", "label": "С момента начала Работ/этапа Работ"}], "conditionals": [{"if_field": "_option", "eq": "exact_date", "then_show_fields": ["prepay_date"]}, {"if_field": "_option", "eq": "from_contract", "then_show_fields": ["prepay_days"]}, {"if_field": "_option", "eq": "from_work", "then_show_fields": ["prepay_days"]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 13"), {"s": s13})

    # Шаг 14: show_if от payment (pay_fact)
    s14 = '''{"info_block": "Оплата при передаче результата.", "show_if": {"step_slug": "payment", "field": "pay_fact"}, "fields": [{"key": "fact_amount", "label": "Сумма (₽)", "type": "number"}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 14"), {"s": s14})

    # Шаг 15: show_if от payment (pay_defer), conditional для defer_reward_pct
    s15 = '''{"info_block": "Оплата спустя время после приёмки.", "show_if": {"step_slug": "payment", "field": "pay_defer"}, "fields": [{"key": "defer_amount", "label": "Сумма (₽)", "type": "number"}, {"key": "defer_days", "label": "Срок отсрочки (дней)", "type": "number"}, {"key": "defer_reward", "label": "Вознаграждение за отсрочку", "type": "checkbox"}, {"key": "defer_reward_pct", "label": "Размер вознаграждения (%)", "type": "number"}], "conditionals": [{"if_field": "defer_reward", "eq": true, "then_show_fields": ["defer_reward_pct"]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 15"), {"s": s15})

    # Шаг 17: переименования, conditionals
    s17 = '''{"info_block": "Неустойки. Оптимально 0,1–1%.", "fields": [{"key": "liab_contractor", "label": "Установить ответственность подрядчика", "type": "checkbox"}, {"key": "liab_contractor_pct", "label": "Размер неустойки в процентах", "type": "number"}, {"key": "liab_increased", "label": "Установить повышенную ответственность за нарушение сроков", "type": "checkbox"}, {"key": "liab_increased_days", "label": "Срок в днях, по истечении которого подрядчик несёт повышенную ответственность", "type": "number"}, {"key": "liab_customer", "label": "Установить ответственность заказчика", "type": "checkbox"}, {"key": "liab_customer_pct", "label": "Размер неустойки в процентах", "type": "number"}], "conditionals": [{"if_field": "liab_contractor", "eq": true, "then_show_fields": ["liab_contractor_pct"]}, {"if_field": "liab_increased", "eq": true, "then_show_fields": ["liab_increased_days"]}, {"if_field": "liab_customer", "eq": true, "then_show_fields": ["liab_customer_pct"]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 17"), {"s": s17})

    # Шаг 18: полные названия опций (с «нахождения»), conditional для claim_days
    s18 = '''{"info_block": "Претензионный порядок и подсудность.", "fields": [{"key": "court_place", "label": "Подсудность", "type": "radio"}, {"key": "claim_required", "label": "Претензионный порядок обязателен", "type": "checkbox"}, {"key": "claim_days", "label": "Срок ответа на претензию (раб. дн.)", "type": "number"}], "options": [{"key": "defendant", "label": "По месту нахождения ответчика"}, {"key": "plaintiff", "label": "По месту нахождения истца"}, {"key": "customer", "label": "По месту нахождения заказчика"}, {"key": "contractor", "label": "По месту нахождения подрядчика"}], "conditionals": [{"if_field": "claim_required", "eq": true, "then_show_fields": ["claim_days"]}]}'''
    conn.execute(text("UPDATE constructor_steps SET schema = CAST(:s AS jsonb) WHERE id = 18"), {"s": s18})


def downgrade() -> None:
    op.drop_column("contract_templates", "constructor_values")
    # Восстановление схем шагов — опускаем (требует сохранения старых значений)
