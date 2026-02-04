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

    async def get_flow_with_steps(
        self, session: AsyncSession, flow_id: int
    ) -> Optional[Dict[str, Any]]:
        """Flow с шагами (schema) для отображения мастера."""
        result = await session.execute(
            select(ConstructorFlow)
            .where(ConstructorFlow.id == flow_id, ConstructorFlow.is_active == True)
            .options(selectinload(ConstructorFlow.steps))
        )
        flow = result.scalar_one_or_none()
        if not flow:
            return None
        steps = sorted(flow.steps, key=lambda s: s.sort_order)
        return {
            "id": flow.id,
            "contract_type_id": flow.contract_type_id,
            "name": flow.name,
            "version": flow.version,
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
