"""Тип «Оферта», конструктор, поля ПЭП, NotificationTypeMeta для оферт и KYC.

Revision ID: offer_edo_260215
Revises: incident_types_260207
Create Date: 2026-02-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "offer_edo_260215"
down_revision: Union[str, Sequence[str], None] = "incident_types_260207"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Фрагменты текста оферты с плейсхолдерами ---

FRAG_HEADER = """<h2>ОФЕРТА</h2>
<p><strong>на заключение договора об оказании услуг</strong></p>
<p>Настоящая Оферта в соответствии с пунктом 2 статьи 437 Гражданского кодекса Российской
Федерации является официальным предложением (публичной офертой) {{ company_name }}
(ОГРН {{ ogrn }}, ИНН {{ inn }}) в лице {{ ceo_position }} {{ ceo_name }},
действующего на основании {{ ceo_basis }}, заключить с {{ company_short_name }} договор оказания услуг на
условиях, определенных в настоящей Оферте, и содержит все существенные условия договора оказания услуг.</p>"""

FRAG_TERMS = """<h3>1. Термины и определения</h3>
<p>1.1. <strong>Заказчик</strong> — {{ company_name }} (ОГРН {{ ogrn }}, ИНН {{ inn }}),
зарегистрированное и действующее по законодательству Российской Федерации,
адрес юридического лица: {{ legal_address }}.</p>
<p>1.2. <strong>Исполнитель</strong> — физическое лицо, зарегистрированное на Сайте и имеющее активный Аккаунт,
обладающее дееспособностью и необходимым полномочием заключить с Заказчиком договор оказания услуг на
условиях, определенных в настоящей Оферте.</p>
<p>1.3. <strong>Стороны</strong> (Сторона) — Заказчик и/или Исполнитель, именуемые совместно (по отдельности).</p>
<p>1.4. <strong>Сайт</strong> — сайт, принадлежащий Заказчику, размещенный по адресу в сети Интернет {{ site_url }}.</p>"""

FRAG_GENERAL = """<h3>2. Общие положения</h3>
<p>2.1. С момента акцепта Исполнителем Оферты в предусмотренном порядке между Исполнителем и
Заказчиком признается заключенным Договор об оказании услуг на условиях настоящей Оферты.</p>
<p>2.2. Договор является договором присоединения (ст. 428 ГК РФ), к которому Исполнитель
присоединяется без каких-либо исключений и/или оговорок.</p>
<p>2.3. Акцепт настоящей Оферты означает, что Исполнитель гарантирует, что ознакомлен и согласен со всеми
положениями и условиями Оферты.</p>
<p>2.4. Договор не требует составления на бумажном носителе, скрепления печатями и/или собственноручными
подписями Сторон, сохраняя при этом полную юридическую силу.</p>"""

FRAG_REGISTRATION = """<h3>3. Регистрация на Сайте</h3>
<p>3.1. Акцептовать настоящую Оферту могут только Исполнители, зарегистрированные на Сайте.</p>
<p>3.2. Исполнитель указывает требуемые данные, необходимые для заключения Договора (включая паспортные
данные, контактный номер телефона, реквизиты расчетного счёта), а также подтверждает переданные данные.</p>
<p>3.3. Исполнитель несет ответственность за достоверность, актуальность и полноту предоставленной информации.</p>"""

FRAG_ACCEPTANCE = """<h3>4. Момент заключения Договора</h3>
<p>4.1. Исполнитель, желающий акцептовать Оферту, должен нажать на кнопку «Принять» в личном кабинете.
После нажатия на кнопку «Принять» на контакт Исполнителя направляется сообщение с кодом подтверждения.</p>
<p>4.2. Акцептом настоящей Оферты является совершение Исполнителем действий по вводу кода подтверждения.</p>
<p>4.3. Совершая действия по акцепту Оферты, Исполнитель гарантирует, что он обладает полной
дееспособностью и необходимым полномочием.</p>"""

FRAG_SUBJECT = """<h3>5. Предмет Договора</h3>
<p>5.1. Исполнитель обязуется по заданию Заказчика оказывать услуги, а Заказчик обязуется оплатить принятые услуги.</p>
<p>5.2. Исполнитель оказывает услуги на основании заявок Заказчика.</p>
<p>5.6. Перечень услуг, которые Исполнитель вправе оказать по Заявке:</p>
{{ service_list }}
<p>5.7. Требования к качеству оказываемых услуг могут быть указаны в Заявке.</p>"""

FRAG_PAYMENT = """<h3>7. Стоимость услуг и порядок оплаты</h3>
<p>7.1. Стоимость услуг размещается на Сайте Заказчика и указывается в Акте о приемке оказанных услуг.</p>
<p>7.2. Заказчик производит оплату за оказанные и принятые услуги (за вычетом НДФЛ) по требованию Исполнителя.
{{ payment_details }}</p>
<p>7.3. Заказчик при оплате Исполнителю исполняет обязанности налогового агента, удерживает и перечисляет НДФЛ — {{ ndfl_rate }}%.</p>"""

FRAG_OBLIGATIONS = """<h3>8. Права и обязанности сторон</h3>
<p>8.1. Исполнитель обязуется оказывать услуги качественно, в объеме и в сроки, согласованные Сторонами.</p>
<p>8.1.5. Не разглашать конфиденциальную информацию Заказчика.</p>
<p>8.2. Заказчик обязуется оплачивать выполненные и принятые услуги.</p>
<p>8.3. Заказчик вправе проверять ход оказания услуг по Договору.</p>"""

FRAG_LIABILITY = """<h3>9. Ответственность сторон</h3>
<p>9.1. За невыполнение или ненадлежащее выполнение обязательств Стороны несут ответственность
в соответствии с действующим законодательством РФ.</p>
<p>9.2. Заказчик вправе потребовать от Исполнителя уплаты штрафов, неустоек и возмещения убытков.</p>
<p>9.3. Заказчик вправе уменьшить вознаграждение Исполнителя на суммы неустоек и штрафов (ст. 410 ГК РФ).</p>"""

FRAG_TERMINATION = """<h3>10. Изменение, расторжение, срок действия Договора</h3>
<p>10.1. Договор вступает в силу с момента совершения акцепта и действует до полного исполнения обязательств.</p>
<p>10.2. Заказчик вправе в любое время отказаться от исполнения Договора в одностороннем порядке.</p>
<p>10.3. Заказчик вправе в одностороннем порядке вносить изменения и/или дополнения в Договор.</p>"""

FRAG_DISPUTES = """<h3>11. Порядок разрешения споров</h3>
<p>11.1. Разногласия разрешаются в обязательном претензионном порядке. Срок ответа на претензию — 10 рабочих дней.</p>
<p>11.3. В случае если досудебный порядок не дал результат, Стороны передают дело в {{ court_name }}.</p>"""

FRAG_CONFIDENTIALITY = """<h3>12. Прочие положения</h3>
<p>12.3. Исполнитель обязуется не раскрывать конфиденциальную информацию. При нарушении — штраф
{{ confidentiality_penalty }} рублей.</p>
<p>12.4. Заключая настоящий Договор, Исполнитель соглашается на обработку его персональных данных.</p>
<p>12.5. Обрабатываемые персональные данные: фамилия, имя, отчество; пол, возраст; дата и место рождения;
паспортные данные; адрес регистрации и адрес проживания; телефон; электронная почта; СНИЛС; банковские реквизиты.</p>"""


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. ContractType "offer" ──
    conn.execute(text(
        "INSERT INTO contract_types (id, code, label) "
        "VALUES (4, 'offer', 'Оферта (договор присоединения)') "
        "ON CONFLICT (code) DO NOTHING"
    ))

    # ── 2. ConstructorFlow для оферты ──
    conn.execute(text(
        "INSERT INTO constructor_flows (id, contract_type_id, name, version, is_active, source) "
        "VALUES (2, 4, 'Оферта на оказание услуг', '1.0', true, 'manual') "
        "ON CONFLICT (id) DO NOTHING"
    ))

    # ── 3. ConstructorSteps (flow_id=2, id=100+) ──
    steps = [
        (101, 2, 1, "Реквизиты заказчика", "company_info",
         '{"info_block": "Данные заказчика подставляются из профиля организации.", '
         '"fields": ['
         '{"key": "company_name", "label": "Полное наименование", "type": "text", "required": true},'
         '{"key": "company_short_name", "label": "Краткое наименование", "type": "text", "required": true},'
         '{"key": "ogrn", "label": "ОГРН", "type": "text", "required": true},'
         '{"key": "inn", "label": "ИНН", "type": "text", "required": true},'
         '{"key": "legal_address", "label": "Юридический адрес", "type": "text", "required": true},'
         '{"key": "ceo_position", "label": "Должность руководителя", "type": "text", "required": true},'
         '{"key": "ceo_name", "label": "ФИО руководителя", "type": "text", "required": true},'
         '{"key": "ceo_basis", "label": "Основание полномочий", "type": "text", "required": true},'
         '{"key": "site_url", "label": "Адрес сайта", "type": "text", "required": false}'
         ']}',
         False),
        (102, 2, 2, "Перечень услуг", "service_types",
         '{"info_block": "Состав услуг, которые исполнитель вправе оказать по заявке (п. 5.6).",'
         '"fields": [{"key": "service_list", "label": "Перечень услуг", "type": "textarea", "required": true,'
         '"placeholder": "Укажите каждую услугу с новой строки"}]}',
         False),
        (103, 2, 3, "Стоимость и оплата", "payment_terms",
         '{"info_block": "Условия оплаты и ставка НДФЛ.",'
         '"fields": ['
         '{"key": "ndfl_rate", "label": "Ставка НДФЛ, %", "type": "number", "required": true, "default": "13"},'
         '{"key": "payment_details", "label": "Дополнительные условия оплаты", "type": "textarea", "required": false}'
         ']}',
         False),
        (104, 2, 4, "Конфиденциальность", "confidentiality",
         '{"info_block": "Сумма штрафа за разглашение (п. 12.3).",'
         '"fields": [{"key": "confidentiality_penalty", "label": "Сумма штрафа (руб.)", "type": "number", "required": true, "default": "100000"}]}',
         False),
        (105, 2, 5, "Подсудность", "jurisdiction",
         '{"info_block": "Суд для разрешения споров (п. 11.3).",'
         '"fields": [{"key": "court_name", "label": "Наименование суда", "type": "text", "required": true}]}',
         False),
        (106, 2, 6, "Сведения о договоре", "contract_info",
         '{"info_block": "Номер и дата — заполняются при заключении.",'
         '"fields": ['
         '{"key": "contract_number", "label": "Номер договора", "type": "text"},'
         '{"key": "sign_date", "label": "Дата подписания", "type": "date"}'
         ']}',
         True),
    ]
    for sid, flow_id, sort_order, title, slug, schema_json, req in steps:
        conn.execute(
            text(
                "INSERT INTO constructor_steps (id, flow_id, sort_order, title, slug, schema, request_at_conclusion) "
                "VALUES (:sid, :flow_id, :sort_order, :title, :slug, CAST(:schema AS jsonb), :req) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"sid": sid, "flow_id": flow_id, "sort_order": sort_order,
             "title": title, "slug": slug, "schema": schema_json, "req": req},
        )

    # ── 4. ConstructorFragments ──
    frags = [
        (101, 101, None, FRAG_HEADER),
        (102, 101, None, FRAG_TERMS),
        (103, 101, None, FRAG_GENERAL),
        (104, 101, None, FRAG_REGISTRATION),
        (105, 101, None, FRAG_ACCEPTANCE),
        (106, 102, None, FRAG_SUBJECT),
        (107, 103, None, FRAG_PAYMENT),
        (108, 103, None, FRAG_OBLIGATIONS),
        (109, 103, None, FRAG_LIABILITY),
        (110, 104, None, FRAG_CONFIDENTIALITY),
        (111, 105, None, FRAG_DISPUTES),
        (112, 105, None, FRAG_TERMINATION),
        (113, 106, None, "<p>Договор № {{ contract_number }} от {{ sign_date }}.</p>"),
    ]
    for fid, step_id, opt_key, content in frags:
        conn.execute(
            text(
                "INSERT INTO constructor_fragments (id, step_id, option_key, fragment_content) "
                "VALUES (:fid, :step_id, :opt_key, :content) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"fid": fid, "step_id": step_id, "opt_key": opt_key, "content": content},
        )

    # ── 5. Новые поля Contract ──
    op.add_column("contracts", sa.Column(
        "pep_metadata", sa.JSON(), nullable=True,
        comment="Метаданные ПЭП: channel, otp_hash, esia_oid, signed_ip",
    ))

    # ── 6. Новое поле ContractVersion ──
    op.add_column("contract_versions", sa.Column(
        "file_key", sa.String(500), nullable=True,
        comment="Ключ подписанного PDF в S3",
    ))

    # ── 7. Seed NotificationTypeMeta для оферт и KYC ──
    ntm_rows = [
        ("offer_sent", "Оферта направлена", "Оферта направлена сотруднику на подписание",
         "contracts", "normal", True, False, '["telegram", "inapp"]', 50),
        ("offer_accepted", "Оферта принята", "Сотрудник принял оферту",
         "contracts", "high", True, False, '["telegram", "inapp"]', 51),
        ("offer_rejected", "Оферта отклонена", "Сотрудник отклонил оферту",
         "contracts", "high", True, False, '["telegram", "inapp"]', 52),
        ("offer_terms_changed", "Условия оферты изменены", "Условия оферты обновлены (автоакцепт)",
         "contracts", "normal", True, False, '["telegram", "inapp"]', 53),
        ("kyc_required", "Требуется верификация", "Для верификации профиля требуется проверка через Госуслуги",
         "verification", "normal", True, False, '["telegram", "inapp"]', 60),
        ("kyc_verified", "Профиль верифицирован", "Профиль успешно верифицирован через Госуслуги",
         "verification", "normal", True, False, '["telegram", "inapp"]', 61),
        ("kyc_failed", "Верификация не пройдена", "Верификация через Госуслуги не пройдена",
         "verification", "high", True, False, '["telegram", "inapp"]', 62),
    ]
    for tc, title, desc, cat, prio, configurable, admin_only, channels, sort in ntm_rows:
        conn.execute(
            text(
                "INSERT INTO notification_types_meta "
                "(type_code, title, description, category, default_priority, "
                "is_user_configurable, is_admin_only, available_channels, sort_order, is_active) "
                "VALUES (:tc, :title, :desc, :cat, :prio, :conf, :adm, CAST(:ch AS jsonb), :sort, true) "
                "ON CONFLICT (type_code) DO NOTHING"
            ),
            {"tc": tc, "title": title, "desc": desc, "cat": cat,
             "prio": prio, "conf": configurable, "adm": admin_only,
             "ch": channels, "sort": sort},
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Удаляем NotificationTypeMeta
    conn.execute(text(
        "DELETE FROM notification_types_meta WHERE type_code IN "
        "('offer_sent','offer_accepted','offer_rejected','offer_terms_changed',"
        "'kyc_required','kyc_verified','kyc_failed')"
    ))

    # Удаляем поля
    op.drop_column("contract_versions", "file_key")
    op.drop_column("contracts", "pep_metadata")

    # Удаляем конструктор оферты
    conn.execute(text("DELETE FROM constructor_fragments WHERE step_id IN (SELECT id FROM constructor_steps WHERE flow_id = 2)"))
    conn.execute(text("DELETE FROM constructor_steps WHERE flow_id = 2"))
    conn.execute(text("DELETE FROM constructor_flows WHERE id = 2"))
    conn.execute(text("DELETE FROM contract_types WHERE code = 'offer'"))
