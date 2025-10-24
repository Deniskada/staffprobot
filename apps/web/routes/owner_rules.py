from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user, require_owner_or_superadmin, get_db_session
from domain.entities.rule import Rule


router = APIRouter()


@router.get("/owner/rules")
async def owner_rules_list(
    request: Request,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    owner_id = current_user.get("db_user_id") or current_user.get("owner_id")
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
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    rule = await session.get(Rule, rule_id)
    if rule:
        rule.is_active = bool(is_active)
        await session.commit()
    return RedirectResponse(url="/owner/rules", status_code=303)


