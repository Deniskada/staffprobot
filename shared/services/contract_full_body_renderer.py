"""
Сервис формирования полного текста договора из full_body шаблона.
Собирает контекст: профили заказчика/подрядчика + values (выборы конструктора).
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.organization_profile import OrganizationProfile
from domain.entities.profile import Profile, IndividualProfile, SoleProprietorProfile, LegalProfile
from domain.entities.user import User
from domain.entities.address import Address
from core.logging.logger import logger


# Сумма прописью (упрощённо)
NUM_WORDS = {
    0: "ноль", 1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять", 10: "десять",
    11: "одиннадцать", 12: "двенадцать", 14: "четырнадцать", 15: "пятнадцать",
}
NUM_ORDERS = [(1e9, "миллиард", "миллиарда", "миллиардов"), (1e6, "миллион", "миллиона", "миллионов"),
              (1e3, "тысяча", "тысячи", "тысяч"), (1, "", "", "")]


def _num_to_words(n: int) -> str:
    """Число прописью (упрощённо для сумм до миллиарда)."""
    if n <= 0:
        return "ноль"
    if n in NUM_WORDS:
        return NUM_WORDS[n]
    for div, one, few, many in NUM_ORDERS:
        if n >= div:
            high, low = divmod(int(n), int(div))
            if div >= 1000:
                high_str = _num_to_words(high) if high > 1 else ""
                if 2 <= high % 10 <= 4 and (high < 10 or high % 100 not in (12, 13, 14)):
                    suffix = few
                elif high % 10 == 1 and high % 100 != 11:
                    suffix = one
                else:
                    suffix = many
                part = f"{high_str} {suffix}".strip() if high_str else suffix
            else:
                part = _num_to_words(high) if high > 1 else one or str(high)
            rest = _num_to_words(low) if low else ""
            return f"{part} {rest}".strip() if rest else part
    return str(n)


def get_preview_context() -> Dict[str, Any]:
    """Контекст-заглушка для превью full_body на странице шаблона."""
    from datetime import datetime
    return {
        "contract_number": "[№]",
        "sign_place": "[Место подписания]",
        "sign_date": datetime.now().strftime("%d.%m.%Y"),
        "customer_party": "[Реквизиты заказчика — указываются при заключении]",
        "contractor_party": "[Реквизиты подрядчика — указываются при заключении]",
        "customer_address": "[Адрес заказчика]",
        "contractor_address": "[Адрес подрядчика]",
        "customer_signature": "[Подпись заказчика]",
        "contractor_signature": "[Подпись подрядчика]",
        "works_list": [],
        "works_default": "[Перечень работ указывается при заключении]",
        "start_date": "[Дата начала]",
        "end_date": "[Дата окончания]",
        "cost": "0",
        "cost_words": "ноль",
        "cost_kopecks": "00",
        "cost_note": "Стоимость определяется при заключении.",
        "payment_terms": "[Порядок оплаты указывается при заключении]",
        "payment_form_text": "[Форма расчётов]",
        "materials_supplier": "Подрядчика",
        "materials_responsible": "Подрядчик",
        "assistance_list": [],
        "quality_list": [],
        "goals_list": [],
        "warranty_text": "",
        "liab_contractor": True,
        "liab_contractor_pct": "0,1",
        "liab_customer": True,
        "liab_customer_pct": "0,1",
        "force_majeure": True,
        "confidentiality": True,
        "claim_required": True,
        "claim_days": "10",
        "court_place": "по месту нахождения подрядчика",
    }


async def build_contract_context(
    session: AsyncSession,
    values: Dict[str, Any],
    owner: User,
    employee: User,
    contract_number: str,
) -> Dict[str, Any]:
    """
    Собирает контекст для рендеринга full_body шаблона.
    values — данные из формы заключения (в т.ч. вложенные по step slug).
    """
    flat = _flatten_values(values)
    flat["contract_number"] = contract_number

    customer = await _get_customer_context(session, owner, values)
    contractor = await _get_contractor_context(session, employee, values)
    flat.update(customer)
    flat.update(contractor)

    _fill_defaults(flat)
    return flat


def _flatten_values(values: Dict[str, Any]) -> Dict[str, Any]:
    """Выравнивает вложенные values (step_choices) в плоский словарь."""
    out: Dict[str, Any] = {}
    works_total = 0
    if not values:
        return out

    ci = values.get("contract_info") or {}
    if isinstance(ci, dict):
        out["sign_place"] = ci.get("sign_place") or values.get("sign_place") or ""
        out["sign_date"] = _fmt_date(ci.get("sign_date") or values.get("sign_date"))
    else:
        out["sign_place"] = values.get("sign_place") or ""
        out["sign_date"] = _fmt_date(values.get("sign_date"))

    obj = values.get("object") or {}
    works_total = 0
    if isinstance(obj, dict):
        works = obj.get("works") or []
        if isinstance(works, list):
            out["works_list"] = []
            for r in works:
                if not r:
                    continue
                if isinstance(r, dict):
                    if any(r.values()):
                        out["works_list"].append(
                            " | ".join(str(r.get(k, "")) for k in ("name", "qty", "unit", "price"))
                        )
                        try:
                            works_total += float(r.get("price") or 0) * float(r.get("qty") or 1)
                        except (TypeError, ValueError):
                            pass
                else:
                    out["works_list"].append(str(r))
        out["works_default"] = "Перечень работ указан в договоре."

    terms = values.get("terms") or {}
    if isinstance(terms, dict):
        out["start_date"] = _fmt_date(terms.get("work_start") or values.get("work_start"))
        out["end_date"] = _fmt_date(terms.get("work_end") or values.get("work_end"))
        supp = terms.get("_option") or terms.get("supplier")
        out["materials_supplier"] = "Подрядчика" if supp == "contractor" else "Заказчика"
        out["materials_responsible"] = "Подрядчик" if supp == "contractor" else "Заказчик"

    cost_step = values.get("cost") or {}
    if isinstance(cost_step, dict):
        out["ndfl"] = cost_step.get("_option") or cost_step.get("ndfl") or "13"
    c = values.get("total_cost") or (cost_step.get("total_amount") if isinstance(cost_step, dict) else None)
    out["cost"] = c if isinstance(c, (int, float)) else (works_total if works_total else 0)
    payment = values.get("payment") or {}
    if isinstance(payment, dict):
        amt = payment.get("amount_type") or "rub"
        out["amount_type"] = "Рубли" if amt == "rub" else "%"
        pf = payment.get("pay_form") or "cashless"
        out["pay_form"] = "Безналичный расчёт" if pf == "cashless" else "Наличный расчёт"
        pd = payment.get("payment_date") or "credit_date"
        out["payment_date"] = "Дата зачисления на счёт получателя" if pd == "credit_date" else "Дата получения банком плат. поручения"

    prepay = values.get("payment_prepay") or {}
    if isinstance(prepay, dict):
        out["prepay_amount"] = prepay.get("prepay_amount", "")
        out["prepay_date"] = _fmt_date(prepay.get("prepay_date"))
        out["prepay_days"] = prepay.get("prepay_days", "")
    fact = values.get("payment_fact") or {}
    if isinstance(fact, dict):
        out["fact_amount"] = fact.get("fact_amount", "")
    defer = values.get("payment_defer") or {}
    if isinstance(defer, dict):
        out["defer_amount"] = defer.get("defer_amount", "")
        out["defer_days"] = defer.get("defer_days", "")
        out["defer_reward_pct"] = defer.get("defer_reward_pct", "")

    acceptance = values.get("acceptance") or {}
    if isinstance(acceptance, dict):
        out["acceptance_days"] = acceptance.get("acceptance_days", "5")
        out["overdue_acceptance_days"] = acceptance.get("overdue_acceptance_days", "5")

    liability = values.get("liability") or {}
    if isinstance(liability, dict):
        out["liab_contractor"] = bool(liability.get("liab_contractor"))
        out["liab_contractor_pct"] = liability.get("liab_contractor_pct", "0,1")
        out["liab_customer"] = bool(liability.get("liab_customer"))
        out["liab_customer_pct"] = liability.get("liab_customer_pct", "0,1")

    disputes = values.get("disputes") or {}
    if isinstance(disputes, dict):
        out["claim_required"] = bool(disputes.get("claim_required"))
        out["claim_days"] = disputes.get("claim_days", "10")
        out["court_place"] = disputes.get("court_place", "по месту нахождения подрядчика")

    misc = values.get("misc") or {}
    if isinstance(misc, dict):
        out["force_majeure"] = bool(misc.get("force_majeure"))
        out["confidentiality"] = bool(misc.get("confidentiality"))

    quality = values.get("quality") or {}
    if isinstance(quality, dict):
        tbl = quality.get("quality") or []
        out["quality_list"] = [r.get("desc", "") for r in tbl if isinstance(r, dict) and r.get("desc")]

    goals_data = values.get("goals") or {}
    if isinstance(goals_data, dict):
        tbl = goals_data.get("goals") or []
        out["goals_list"] = [r.get("desc", "") for r in tbl if isinstance(r, dict) and r.get("desc")]

    assist = values.get("assistance") or {}
    if isinstance(assist, dict):
        tbl = assist.get("assistance") or []
        out["assistance_list"] = [r.get("desc", "") for r in tbl if isinstance(r, dict) and r.get("desc")]

    warranty = values.get("warranty") or {}
    if isinstance(warranty, dict):
        opt = warranty.get("_option")
        if opt == "by_date":
            out["warranty_text"] = f"Гарантия до {_fmt_date(warranty.get('warranty_date'))}."
        elif opt == "by_period":
            cnt = warranty.get("warranty_count", "")
            unit = warranty.get("warranty_unit", "дней")
            out["warranty_text"] = f"Гарантия {cnt} {unit} с момента приёмки."
        else:
            out["warranty_text"] = ""

    if not out.get("start_date"):
        out["start_date"] = _fmt_date(values.get("work_start"))
    if not out.get("end_date"):
        out["end_date"] = _fmt_date(values.get("work_end"))

    return out


def _fmt_date(val: Any) -> str:
    if not val:
        return ""
    if isinstance(val, (date, datetime)):
        return val.strftime("%d.%m.%Y")
    if isinstance(val, str) and len(val) >= 10:
        try:
            d = datetime.fromisoformat(val[:10].replace("Z", ""))
            return d.strftime("%d.%m.%Y")
        except ValueError:
            pass
    return str(val) if val else ""


async def _get_customer_context(
    session: AsyncSession, owner: User, values: Dict[str, Any]
) -> Dict[str, Any]:
    """Реквизиты заказчика из OrganizationProfile или Profile владельца."""
    profile_id = None
    if isinstance(values.get("customer_profile_id"), (int, str)):
        try:
            profile_id = int(values["customer_profile_id"])
        except (TypeError, ValueError):
            pass

    org = await _get_default_organization_profile(session, owner.id)
    if org and org.requisites:
        r = org.requisites
        name = r.get("owner_fullname") or r.get("company_full_name") or org.profile_name
        inn = r.get("owner_inn") or r.get("company_inn") or ""
        ogrn = r.get("owner_ogrnip") or r.get("company_ogrn") or ""
        addr = r.get("owner_registration_address") or r.get("company_legal_address") or ""
        party = f"{name}"
        if inn:
            party += f", ИНН: {inn}"
        if ogrn:
            party += f", ОГРНИП {ogrn}" if "огрнип" in str(ogrn).lower() or "owner" in str(r) else f", ОГРН {ogrn}"
        party += " (далее – «Заказчик»)"
        return {
            "customer_party": party,
            "customer_address": addr or f"{name}",
            "customer_signature": (name.split()[-2] + " " + name.split()[-1][:1] + ".") if name else "",
            "customer_fullname": name,
            "customer_inn": inn,
        }

    prof = await _get_default_profile(session, owner.id, profile_id)
    if prof:
        d = await _profile_to_contract_dict(session, prof)
        name = d.get("display_name", f"{owner.first_name or ''} {owner.last_name or ''}".strip())
        addr = d.get("address_full", "")
        party = f"{name} (далее – «Заказчик»)"
        return {
            "customer_party": party,
            "customer_address": addr or name,
            "customer_signature": name.split()[-1] if name else "",
            "customer_fullname": name,
        }

    name = f"{owner.first_name or ''} {owner.last_name or ''}".strip() or str(owner.id)
    return {
        "customer_party": f"{name} (далее – «Заказчик»)",
        "customer_address": name,
        "customer_signature": name.split()[-1] if name else "",
        "customer_fullname": name,
    }


async def _get_contractor_context(
    session: AsyncSession, employee: User, values: Dict[str, Any]
) -> Dict[str, Any]:
    """Реквизиты подрядчика из Profile (IndividualProfile) сотрудника."""
    profile_id = None
    if isinstance(values.get("contractor_profile_id"), (int, str)):
        try:
            profile_id = int(values["contractor_profile_id"])
        except (TypeError, ValueError):
            pass

    prof = await _get_default_profile(session, employee.id, profile_id)
    if prof:
        d = await _profile_to_contract_dict(session, prof)
        name = d.get("display_name", "")
        pas = d.get("passport_str", "")
        addr = d.get("address_full", "")
        party = name
        if pas:
            party += f", {pas}"
        if addr:
            party += f", зарегистрирован по адресу: {addr}"
        party += " (далее – «Подрядчик»)"
        return {
            "contractor_party": party,
            "contractor_address": addr or name,
            "contractor_signature": (name.split()[-2] + " " + name.split()[-1][:1] + ".") if name else "",
            "contractor_fullname": name,
        }

    name = f"{employee.first_name or ''} {employee.last_name or ''}".strip() or str(employee.id)
    return {
        "contractor_party": f"{name} (далее – «Подрядчик»)",
        "contractor_address": name,
        "contractor_signature": name.split()[-1] if name else "",
        "contractor_fullname": name,
    }


async def _get_default_organization_profile(
    session: AsyncSession, user_id: int
) -> Optional[OrganizationProfile]:
    r = await session.execute(
        select(OrganizationProfile)
        .where(OrganizationProfile.user_id == user_id)
        .order_by(OrganizationProfile.is_default.desc(), OrganizationProfile.id)
        .limit(1)
    )
    return r.scalar_one_or_none()


async def _get_default_profile(
    session: AsyncSession, user_id: int, profile_id: Optional[int] = None
) -> Optional[Profile]:
    if profile_id:
        r = await session.execute(
            select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
        )
        p = r.scalar_one_or_none()
        if p:
            return p
    r = await session.execute(
        select(Profile)
        .where(Profile.user_id == user_id, Profile.is_archived.is_(False))
        .order_by(Profile.is_default.desc(), Profile.id)
        .limit(1)
    )
    return r.scalar_one_or_none()


async def _profile_to_contract_dict(session: AsyncSession, profile: Profile) -> Dict[str, Any]:
    """Преобразует Profile в словарь для шаблона договора."""
    d: Dict[str, Any] = {"display_name": profile.display_name or ""}
    if profile.profile_type == "individual":
        inst = await session.execute(
            select(IndividualProfile).where(IndividualProfile.profile_id == profile.id)
        )
        ip = inst.scalar_one_or_none()
        if ip:
            d["display_name"] = f"{ip.last_name or ''} {ip.first_name or ''} {ip.middle_name or ''}".strip()
            pas = []
            if ip.passport_series:
                pas.append(ip.passport_series)
            if ip.passport_number:
                pas.append(str(ip.passport_number))
            if pas:
                d["passport_str"] = f"паспорт {' '.join(pas)}"
                if ip.passport_issued_by:
                    d["passport_str"] += f", выдан {ip.passport_issued_by}"
                if ip.passport_issued_at:
                    d["passport_str"] += f" {ip.passport_issued_at.strftime('%d.%m.%Y')}"
                if ip.passport_department_code:
                    d["passport_str"] += f", код подразделения {ip.passport_department_code}"
            else:
                d["passport_str"] = ""
            addr = ""
            if ip.registration_address_id:
                res = await session.execute(
                    select(Address.full_address).where(Address.id == ip.registration_address_id)
                )
                addr = res.scalar_one_or_none() or ""
            d["address_full"] = addr
    elif profile.profile_type == "sole_proprietor":
        inst = await session.execute(
            select(SoleProprietorProfile).where(SoleProprietorProfile.profile_id == profile.id)
        )
        sp = inst.scalar_one_or_none()
        if sp:
            d["display_name"] = f"{sp.last_name or ''} {sp.first_name or ''} {sp.middle_name or ''}".strip()
            addr = ""
            if sp.residence_address_id:
                res = await session.execute(
                    select(Address.full_address).where(Address.id == sp.residence_address_id)
                )
                addr = res.scalar_one_or_none() or ""
            d["address_full"] = addr
            d["passport_str"] = ""
    elif profile.profile_type == "legal":
        inst = await session.execute(
            select(LegalProfile).where(LegalProfile.profile_id == profile.id)
        )
        lp = inst.scalar_one_or_none()
        if lp:
            d["display_name"] = lp.full_name or profile.display_name
            addr = ""
            if lp.registration_address_id:
                res = await session.execute(
                    select(Address.full_address).where(Address.id == lp.registration_address_id)
                )
                addr = res.scalar_one_or_none() or ""
            d["address_full"] = addr
            d["passport_str"] = ""
    return d


def _fill_defaults(ctx: Dict[str, Any]) -> None:
    """Заполняет обязательные поля значениями по умолчанию и форматирует."""
    ctx.setdefault("sign_place", "")
    ctx.setdefault("sign_date", datetime.now().strftime("%d.%m.%Y"))
    ctx.setdefault("works_list", [])
    ctx.setdefault("works_default", "Перечень работ указан в договоре.")
    ctx.setdefault("start_date", "")
    ctx.setdefault("end_date", "")
    cost = ctx.get("cost") or 0
    try:
        cost = int(float(cost))
    except (TypeError, ValueError):
        cost = 0
    ctx["cost"] = f"{cost:,}".replace(",", " ")
    ctx["cost_words"] = _num_to_words(cost)
    ctx["cost_kopecks"] = "00"
    ctx.setdefault("cost_note", "Стоимость является твёрдой.")
    terms = []
    if ctx.get("prepay_amount"):
        terms.append(
            f"Заказчик выплачивает предоплату {ctx['prepay_amount']} ₽"
            + (f" до {ctx.get('prepay_date', '')}" if ctx.get("prepay_date") else "")
            + (f" в течение {ctx.get('prepay_days', '')} дней с начала работ" if ctx.get("prepay_days") else "")
            + "."
        )
    if ctx.get("fact_amount"):
        terms.append(f"По факту завершения Работ — {ctx['fact_amount']} ₽.")
    if ctx.get("defer_amount"):
        terms.append(
            f"Отсрочка {ctx['defer_amount']} ₽, {ctx.get('defer_days', '')} дн."
            + (f" Вознаграждение за отсрочку {ctx.get('defer_reward_pct', '')}%." if ctx.get("defer_reward_pct") else "")
        )
    ctx["payment_terms"] = " ".join(terms) if terms else "Оплата по согласованию сторон."
    ctx["payment_form_text"] = f"Расчёты производятся {ctx.get('pay_form', 'безналично')}."
    ctx.setdefault("materials_supplier", "Подрядчика")
    ctx.setdefault("materials_responsible", "Подрядчик")
    ctx.setdefault("assistance_list", [])
    ctx.setdefault("quality_list", [])
    ctx.setdefault("goals_list", [])
    ctx.setdefault("warranty_text", "")
    ctx.setdefault("liab_contractor", False)
    ctx.setdefault("liab_contractor_pct", "0,1")
    ctx.setdefault("liab_customer", False)
    ctx.setdefault("liab_customer_pct", "0,1")
    ctx.setdefault("force_majeure", True)
    ctx.setdefault("confidentiality", True)
    ctx.setdefault("claim_required", True)
    ctx.setdefault("claim_days", "10")
    ctx.setdefault("court_place", "по месту нахождения подрядчика")
