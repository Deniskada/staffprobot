from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.rule import Rule
from domain.entities.user import User


router = APIRouter()


@router.get("/owner/rules")
async def owner_rules_list(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    owner_id = getattr(current_user, "id", None)
    query = select(Rule).where((Rule.owner_id == owner_id) | (Rule.owner_id.is_(None))).order_by(Rule.scope, Rule.priority, Rule.id)
    result = await session.execute(query)
    rules = result.scalars().all()
    return templates.TemplateResponse(
        "owner/rules/list.html",
        {"request": request, "rules": rules}
    )


@router.post("/owner/rules/toggle")
async def owner_rules_toggle(
    rule_id: int = Form(...),
    is_active: int = Form(...),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    rule = await session.get(Rule, rule_id)
    if rule:
        rule.is_active = bool(is_active)
        await session.commit()
    return RedirectResponse(url="/owner/rules", status_code=303)


@router.post("/owner/rules/seed")
async def owner_rules_seed(
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """SEED стартовых правил из текущих настроек объектов/org_units владельца."""
    from domain.entities.object import Object
    from domain.entities.org_structure import OrgStructureUnit
    import json
    owner_id = current_user.id
    
    # Late penalties: сканируем объекты и org_units
    objs_query = select(Object).where(Object.owner_id == owner_id)
    objs_res = await session.execute(objs_query)
    objs = objs_res.scalars().all()
    
    # Правило по умолчанию для late: если obj имеет late_threshold_minutes и late_penalty_per_minute
    for obj in objs:
        if obj.late_threshold_minutes and obj.late_penalty_per_minute:
            code = f"late_default_obj{obj.id}"
            rule = Rule(
                owner_id=owner_id,
                code=code,
                name=f"Штраф за опоздание (объект {obj.name})",
                scope="late",
                priority=100,
                is_active=True,
                condition_json=json.dumps({"object_id": obj.id}),
                action_json=json.dumps({
                    "type": "fine",
                    "amount": float(obj.late_threshold_minutes) * float(obj.late_penalty_per_minute),
                    "label": f"Штраф за опоздание (>{obj.late_threshold_minutes} мин)",
                    "code": code
                })
            )
            session.add(rule)
    
    # Cancellation penalties
    for obj in objs:
        if obj.cancellation_short_notice_fine and obj.cancellation_short_notice_hours:
            code = f"cancel_short_obj{obj.id}"
            rule = Rule(
                owner_id=owner_id,
                code=code,
                name=f"Штраф за отмену в короткий срок (объект {obj.name})",
                scope="cancellation",
                priority=100,
                is_active=True,
                condition_json=json.dumps({"object_id": obj.id}),
                action_json=json.dumps({
                    "type": "fine",
                    "amount": float(obj.cancellation_short_notice_fine),
                    "fine_code": "short_notice",
                    "label": f"Штраф за отмену <{obj.cancellation_short_notice_hours}ч",
                    "code": code
                })
            )
            session.add(rule)
        
        if obj.cancellation_invalid_reason_fine:
            code = f"cancel_invalid_obj{obj.id}"
            rule = Rule(
                owner_id=owner_id,
                code=code,
                name=f"Штраф за неуважительную отмену (объект {obj.name})",
                scope="cancellation",
                priority=200,
                is_active=True,
                condition_json=json.dumps({"object_id": obj.id}),
                action_json=json.dumps({
                    "type": "fine",
                    "amount": float(obj.cancellation_invalid_reason_fine),
                    "fine_code": "invalid_reason",
                    "label": "Штраф за неуважительную причину",
                    "code": code
                })
            )
            session.add(rule)
    
    await session.commit()
    return RedirectResponse(url="/owner/rules", status_code=303)


