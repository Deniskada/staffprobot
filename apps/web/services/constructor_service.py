"""Сервис сборки шаблона договора из шагов конструктора и фрагментов."""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.contract import ContractTemplate
from domain.entities.contract_type import ContractType
from domain.entities.constructor_flow import ConstructorFlow, ConstructorStep, ConstructorFragment
from domain.entities.user import User


class ConstructorService:
    """Сборка контента шаблона из step_choices и фрагментов."""

    async def get_contract_types(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Список типов договоров."""
        result = await session.execute(select(ContractType).order_by(ContractType.id))
        rows = result.scalars().all()
        return [{"id": r.id, "code": r.code, "label": r.label} for r in rows]

    async def get_contract_type_full_body(
        self, session: AsyncSession, type_id: int
    ) -> Optional[Dict[str, Any]]:
        """Получить full_body типа договора."""
        result = await session.execute(
            select(ContractType).where(ContractType.id == type_id)
        )
        ct = result.scalar_one_or_none()
        if not ct:
            return None
        return {"id": ct.id, "label": ct.label, "full_body": ct.full_body or ""}

    async def update_contract_type_full_body(
        self, session: AsyncSession, type_id: int, full_body: str
    ) -> bool:
        """Обновить full_body типа договора."""
        result = await session.execute(
            select(ContractType).where(ContractType.id == type_id)
        )
        ct = result.scalar_one_or_none()
        if not ct:
            return False
        ct.full_body = full_body
        await session.commit()
        return True

    async def get_flows(
        self, session: AsyncSession, contract_type_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Список активных flows, опционально по типу договора."""
        q = (
            select(ConstructorFlow)
            .where(ConstructorFlow.is_active == True)
            .order_by(ConstructorFlow.id)
        )
        if contract_type_id is not None:
            q = q.where(ConstructorFlow.contract_type_id == contract_type_id)
        result = await session.execute(q)
        flows = result.scalars().all()
        return [
            {
                "id": f.id,
                "contract_type_id": f.contract_type_id,
                "name": f.name,
                "version": f.version,
            }
            for f in flows
        ]

    async def get_flows_for_editor(
        self, session: AsyncSession
    ) -> Dict[str, Any]:
        """Все flows для редактора, сгруппированные по типу договора."""
        result = await session.execute(
            select(ConstructorFlow, ContractType.label)
            .join(ContractType, ConstructorFlow.contract_type_id == ContractType.id)
            .order_by(ContractType.id, ConstructorFlow.id)
        )
        rows = result.all()
        by_type: Dict[int, Dict[str, Any]] = {}
        for flow, type_label in rows:
            tid = flow.contract_type_id
            if tid not in by_type:
                by_type[tid] = {
                    "contract_type_id": tid,
                    "contract_type_label": type_label,
                    "flows": [],
                }
            by_type[tid]["flows"].append({
                "id": flow.id,
                "name": flow.name,
                "version": flow.version,
                "is_active": flow.is_active,
            })
        return {"by_contract_type": list(by_type.values())}

    async def update_flow(
        self,
        session: AsyncSession,
        flow_id: int,
        name: Optional[str] = None,
        version: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Обновить flow (name, version, is_active)."""
        result = await session.execute(
            select(ConstructorFlow).where(ConstructorFlow.id == flow_id)
        )
        flow = result.scalar_one_or_none()
        if not flow:
            return False
        if name is not None:
            flow.name = name
        if version is not None:
            flow.version = version
        if is_active is not None:
            flow.is_active = is_active
        await session.commit()
        return True

    async def update_step(
        self,
        session: AsyncSession,
        step_id: int,
        title: Optional[str] = None,
        slug: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        request_at_conclusion: Optional[bool] = None,
        sort_order: Optional[int] = None,
    ) -> bool:
        """Обновить шаг."""
        result = await session.execute(
            select(ConstructorStep).where(ConstructorStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if not step:
            return False
        if title is not None:
            step.title = title
        if slug is not None:
            step.slug = slug
        if schema is not None:
            step.schema = schema
        if request_at_conclusion is not None:
            step.request_at_conclusion = request_at_conclusion
        if sort_order is not None:
            step.sort_order = sort_order
        await session.commit()
        return True

    async def reorder_steps(
        self, session: AsyncSession, flow_id: int, step_ids: List[int]
    ) -> bool:
        """Установить порядок шагов по списку id."""
        for idx, sid in enumerate(step_ids):
            result = await session.execute(
                select(ConstructorStep).where(
                    ConstructorStep.id == sid,
                    ConstructorStep.flow_id == flow_id,
                )
            )
            step = result.scalar_one_or_none()
            if step:
                step.sort_order = idx
        await session.commit()
        return True

    async def get_flow_by_id(
        self, session: AsyncSession, flow_id: int, for_editor: bool = False
    ) -> Optional[ConstructorFlow]:
        """Flow по id. for_editor=True — без фильтра is_active."""
        q = select(ConstructorFlow).where(ConstructorFlow.id == flow_id)
        if not for_editor:
            q = q.where(ConstructorFlow.is_active == True)
        result = await session.execute(q.options(selectinload(ConstructorFlow.steps)))
        return result.scalar_one_or_none()

    async def get_flow_with_steps(
        self, session: AsyncSession, flow_id: int
    ) -> Optional[Dict[str, Any]]:
        """Flow с шагами (schema) для отображения мастера."""
        flow = await self.get_flow_by_id(session, flow_id, for_editor=False)
        if not flow:
            return None
        steps = sorted(flow.steps, key=lambda s: s.sort_order)
        return {
            "id": flow.id,
            "contract_type_id": flow.contract_type_id,
            "name": flow.name,
            "version": flow.version,
            "is_active": flow.is_active,
            "steps": [
                {
                    "id": s.id,
                    "sort_order": s.sort_order,
                    "title": s.title,
                    "slug": s.slug,
                    "schema": s.schema or {},
                    "request_at_conclusion": s.request_at_conclusion,
                }
                for s in steps
            ],
        }

    async def get_fragments_for_step(
        self, session: AsyncSession, step_id: int
    ) -> List[Dict[str, Any]]:
        """Фрагменты шага для редактора (с id)."""
        result = await session.execute(
            select(ConstructorFragment).where(ConstructorFragment.step_id == step_id)
        )
        frags = result.scalars().all()
        return [
            {"id": f.id, "option_key": f.option_key, "fragment_content": f.fragment_content}
            for f in frags
        ]

    async def update_fragment(
        self,
        session: AsyncSession,
        fragment_id: int,
        fragment_content: str,
    ) -> bool:
        """Обновить fragment_content."""
        result = await session.execute(
            select(ConstructorFragment).where(ConstructorFragment.id == fragment_id)
        )
        frag = result.scalar_one_or_none()
        if not frag:
            return False
        frag.fragment_content = fragment_content
        await session.commit()
        return True

    async def get_fragments_by_flow(
        self, session: AsyncSession, flow_id: int
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Фрагменты по step_id для сборки (step_id -> [{option_key, fragment_content}])."""
        result = await session.execute(
            select(ConstructorFragment).join(
                ConstructorStep, ConstructorFragment.step_id == ConstructorStep.id
            ).where(ConstructorStep.flow_id == flow_id)
        )
        frags = result.scalars().all()
        by_step: Dict[int, List[Dict[str, Any]]] = {}
        for f in frags:
            by_step.setdefault(f.step_id, []).append(
                {"option_key": f.option_key, "fragment_content": f.fragment_content}
            )
        return by_step

    async def build_template(
        self,
        session: AsyncSession,
        flow_id: int,
        step_choices: Dict[str, Any],
        template_name: str,
        template_description: str,
        created_by_telegram_id: int,
        contract_type_id: Optional[int] = None,
    ) -> Optional[ContractTemplate]:
        """
        Собрать content из фрагментов по step_choices и создать ContractTemplate.
        step_choices: { "step_slug": "option_key" | { "field_key": value, ... } }
        """
        flow_result = await session.execute(
            select(ConstructorFlow)
            .where(ConstructorFlow.id == flow_id, ConstructorFlow.is_active == True)
            .options(
                selectinload(ConstructorFlow.steps).selectinload(ConstructorStep.fragments)
            )
        )
        flow = flow_result.scalar_one_or_none()
        if not flow:
            return None

        user_result = await session.execute(
            select(User).where(User.telegram_id == created_by_telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"Пользователь с Telegram ID {created_by_telegram_id} не найден")

        steps = sorted(flow.steps, key=lambda s: s.sort_order)
        parts: List[str] = []
        fields_schema: List[Dict[str, Any]] = []
        choices = step_choices if isinstance(step_choices, dict) else {}

        for step in steps:
            schema = step.schema or {}
            show_if = schema.get("show_if")
            if isinstance(show_if, dict):
                ref_slug = show_if.get("step_slug")
                ref_field = show_if.get("field")
                if ref_slug and ref_field:
                    ref_choice = choices.get(ref_slug)
                    ref_val = ref_choice.get(ref_field) if isinstance(ref_choice, dict) else None
                    if not ref_val:
                        continue

            # Пункт «Сведения о договоре» (номер, место, дата) заполняется при заключении — в превью не выводим
            if step.slug == "contract_info":
                if step.request_at_conclusion and schema:
                    for f in schema.get("fields", []):
                        key = f.get("key")
                        if key and isinstance(key, str):
                            fields_schema.append({
                                "key": str(key),
                                "label": str(f.get("label", key)),
                                "type": str(f.get("type", "text")),
                                "required": bool(f.get("required", False)),
                            })
                continue

            choice = choices.get(step.slug)
            fragments_for_step = {f.option_key: f.fragment_content for f in step.fragments}

            if step.request_at_conclusion and schema:
                for f in schema.get("fields", []):
                    key = f.get("key")
                    if key and isinstance(key, str):
                        fields_schema.append({
                            "key": str(key),
                            "label": str(f.get("label", key)),
                            "type": str(f.get("type", "text")),
                            "required": bool(f.get("required", False)),
                        })

            option_key = None
            field_values: Dict[str, Any] = {}
            if isinstance(choice, str):
                option_key = choice
            elif isinstance(choice, dict):
                option_key = choice.get("_option")
                field_values = {k: v for k, v in choice.items() if k != "_option"}
            if option_key is not None:
                field_values["_option"] = option_key

            content = fragments_for_step.get(option_key) or fragments_for_step.get(None)
            if not content:
                continue

            resolved = self._resolve_display_values(field_values, schema, option_key)
            content = self._substitute_placeholders(content, resolved)
            parts.append(content)

        full_content = "\n\n".join(parts) if parts else ""

        # Автоподстановка данных владельца из профиля
        owner_data = await self._load_owner_profile_data(session, user.id)
        if owner_data:
            full_content = self._substitute_placeholders(full_content, owner_data)

        template = ContractTemplate(
            name=template_name,
            description=template_description or "",
            content=full_content,
            version="1.0",
            created_by=user.id,
            is_public=False,
            fields_schema=fields_schema if fields_schema else None,
            contract_type_id=contract_type_id or flow.contract_type_id,
            constructor_flow_id=flow_id,
            constructor_values=choices,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template, attribute_names=["id", "name", "created_at"])
        logger.info("Constructor template created", template_id=template.id, template_name=template_name)
        return template

    async def _load_owner_profile_data(
        self, session: AsyncSession, user_id: int
    ) -> Dict[str, str]:
        """
        Загрузить данные дефолтного профиля владельца для автоподстановки.

        Поддерживаемые плейсхолдеры:
          ЮЛ: company_name, company_short_name, ogrn, inn, legal_address, ceo_name, ceo_basis
          ИП: company_name, inn, ogrnip, legal_address
          ФЛ: company_name (ФИО), inn, snils
        """
        from domain.entities.profile import (
            Profile, LegalProfile, SoleProprietorProfile, IndividualProfile,
        )
        from domain.entities.address import Address

        stmt = (
            select(Profile)
            .where(Profile.user_id == user_id, Profile.is_archived.is_(False))
            .order_by(Profile.is_default.desc(), Profile.id)
        )
        result = await session.execute(stmt)
        profile = result.scalars().first()
        if not profile:
            return {}

        data: Dict[str, str] = {}

        if profile.profile_type == "legal":
            lp_result = await session.execute(
                select(LegalProfile).where(LegalProfile.profile_id == profile.id)
            )
            lp = lp_result.scalar_one_or_none()
            if lp:
                data["company_name"] = lp.full_name or ""
                data["company_short_name"] = profile.display_name or lp.full_name or ""
                data["ogrn"] = lp.ogrn or ""
                data["inn"] = lp.inn or ""
                if lp.registration_address_id:
                    addr = await session.get(Address, lp.registration_address_id)
                    data["legal_address"] = addr.full_address if addr else ""
                if lp.representative_profile_id:
                    rep = await session.get(IndividualProfile, lp.representative_profile_id)
                    if rep:
                        middle = f" {rep.middle_name}" if rep.middle_name else ""
                        data["ceo_name"] = f"{rep.last_name} {rep.first_name}{middle}"
                data["ceo_basis"] = lp.representative_basis or "Устав"

        elif profile.profile_type == "sole_proprietor":
            sp_result = await session.execute(
                select(SoleProprietorProfile).where(SoleProprietorProfile.profile_id == profile.id)
            )
            sp = sp_result.scalar_one_or_none()
            if sp:
                middle = f" {sp.middle_name}" if sp.middle_name else ""
                data["company_name"] = f"ИП {sp.last_name} {sp.first_name}{middle}"
                data["company_short_name"] = data["company_name"]
                data["inn"] = sp.inn or ""
                data["ogrnip"] = sp.ogrnip or ""
                data["ogrn"] = sp.ogrnip or ""
                data["ceo_name"] = f"{sp.last_name} {sp.first_name}{middle}"
                data["ceo_basis"] = "свидетельство о государственной регистрации"
                if sp.residence_address_id:
                    addr = await session.get(Address, sp.residence_address_id)
                    data["legal_address"] = addr.full_address if addr else ""

        elif profile.profile_type == "individual":
            ip_result = await session.execute(
                select(IndividualProfile).where(IndividualProfile.profile_id == profile.id)
            )
            ip = ip_result.scalar_one_or_none()
            if ip:
                middle = f" {ip.middle_name}" if ip.middle_name else ""
                data["company_name"] = f"{ip.last_name} {ip.first_name}{middle}"
                data["company_short_name"] = data["company_name"]
                data["inn"] = ip.inn or ""
                data["snils"] = ip.snils or ""
                data["ceo_name"] = data["company_name"]
                if ip.registration_address_id:
                    addr = await session.get(Address, ip.registration_address_id)
                    data["legal_address"] = addr.full_address if addr else ""

        return data

    @staticmethod
    def _resolve_display_values(
        field_values: Dict[str, Any], schema: Dict[str, Any], option_key: Optional[str]
    ) -> Dict[str, Any]:
        """Преобразует значения для отображения: bool→да/нет, дата→DD.MM.YYYY, ключи опций→label."""
        options_list = (schema or {}).get("options") or []
        key_to_label = {opt.get("key"): opt.get("label", opt.get("key")) for opt in options_list if opt.get("key")}
        fields_by_key = {}
        options_by_field: Dict[str, Dict[str, str]] = {}
        for f in (schema or {}).get("fields") or []:
            k = f.get("key")
            if k:
                fields_by_key[k] = f
                for opt in f.get("options") or []:
                    if opt.get("key"):
                        options_by_field.setdefault(k, {})[opt["key"]] = opt.get("label", opt["key"])
        result = {}
        for key, val in field_values.items():
            if val is None:
                result[key] = ""
                continue
            if isinstance(val, list):
                result[key] = val
                continue
            if isinstance(val, bool):
                result[key] = "да" if val else "нет"
                continue
            if isinstance(val, (date, datetime)):
                result[key] = _format_date(val)
                continue
            if isinstance(val, str) and _looks_like_date(val):
                result[key] = _format_date_string(val)
                continue
            if key == "_option" and option_key and option_key in key_to_label:
                result[key] = key_to_label[option_key]
                continue
            if key in options_by_field and str(val) in options_by_field[key]:
                result[key] = options_by_field[key][str(val)]
                continue
            if key in fields_by_key and (fields_by_key[key].get("type") in ("radio", "select")) and str(val) in key_to_label:
                result[key] = key_to_label[str(val)]
                continue
            result[key] = val
        return result

    @staticmethod
    def _substitute_placeholders(content: str, values: Dict[str, Any]) -> str:
        """Подстановка {{ key }} в content. Непереданные ключи заменяются на пустую строку."""
        for key, val in values.items():
            placeholder = "{{ " + key + " }}"
            if placeholder not in content:
                continue
            if isinstance(val, list):
                text = _format_table_rows(val)
            else:
                text = str(val) if val is not None else ""
            content = content.replace(placeholder, text)
        # Оставшиеся плейсхолдеры (нет в values) — пустая строка
        content = re.sub(r"\{\{\s*\w+\s*\}\}", "", content)
        return content


def _format_date(d: date) -> str:
    """Дата в формате DD.MM.YYYY."""
    return d.strftime("%d.%m.%Y")


def _looks_like_date(s: str) -> bool:
    """Проверка, похожа ли строка на ISO-дату (YYYY-MM-DD)."""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", s or ""))


def _format_date_string(s: str) -> str:
    """Строка даты ISO → DD.MM.YYYY."""
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y")
        parts = s.strip()[:10].split("-")
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{d:02d}.{m:02d}.{y:04d}"
    except (ValueError, IndexError):
        pass
    return s


def _format_table_rows(rows: List[Dict[str, Any]]) -> str:
    """Форматирование строк таблицы в текст (например, для вставки в договор)."""
    if not rows:
        return ""
    lines = []
    for row in rows:
        line = " | ".join(str(v) for v in row.values() if v is not None and str(v).strip())
        if line.strip():
            lines.append(line)
    return "\n".join(lines)
