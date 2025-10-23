"""Управление причинами отмен владельцем."""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.database.session import get_db_session
from apps.web.jinja import templates
from domain.entities.user import User
from domain.entities.cancellation_reason import CancellationReason

router = APIRouter()


@router.get("/owner/cancellations/reasons", response_class=HTMLResponse)
async def owner_cancellation_reasons_page(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница управления причинами отмен (для владельца)."""
    # telegram_id текущего
    user_query = select(User).where(User.telegram_id == current_user.get("id"))
    user = (await db.execute(user_query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # 1) Загружаем причины владельца
    owner_reasons_q = (
        select(CancellationReason)
        .where(CancellationReason.owner_id == user.id)
        .order_by(CancellationReason.order_index, CancellationReason.id)
    )
    owner_reasons = (await db.execute(owner_reasons_q)).scalars().all()

    # 2) Загружаем глобальные причины, которых нет у владельца (чтобы не было дублей)
    owner_codes = {r.code for r in owner_reasons}
    global_reasons_q = (
        select(CancellationReason)
        .where(
            CancellationReason.owner_id.is_(None),
        )
        .order_by(CancellationReason.order_index, CancellationReason.id)
    )
    global_reasons = [r for r in (await db.execute(global_reasons_q)).scalars().all() if r.code not in owner_codes]

    reasons = owner_reasons + global_reasons

    return templates.TemplateResponse("owner/cancellations/reasons.html", {
        "request": request,
        "current_user": current_user,
        "reasons": reasons,
    })


@router.post("/owner/cancellations/reasons/update")
async def owner_cancellation_reasons_update(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    form = await request.form()
    user_query = select(User).where(User.telegram_id == current_user.get("id"))
    user = (await db.execute(user_query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Ожидаем поля вида code[], title[], requires_document[code], treated_as_valid[code], is_active[code], is_employee_visible[code], order_index[code]
    codes: List[str] = form.getlist("code[]")
    titles: List[str] = form.getlist("title[]")

    existing_query = select(CancellationReason).where(CancellationReason.owner_id == user.id)
    existing = {r.code: r for r in (await db.execute(existing_query)).scalars().all()}

    for idx, code in enumerate(codes):
        title = titles[idx] if idx < len(titles) else code
        requires_document = form.get(f"requires_document[{code}]") == "on"
        treated_as_valid = form.get(f"treated_as_valid[{code}]") == "on"
        is_active = form.get(f"is_active[{code}]") == "on"
        is_employee_visible = form.get(f"is_employee_visible[{code}]") == "on"
        order_index_str = form.get(f"order_index[{code}]") or "0"
        try:
            order_index = int(order_index_str)
        except ValueError:
            order_index = 0

        entity = existing.get(code)
        if entity:
            entity.title = title
            entity.requires_document = requires_document
            entity.treated_as_valid = treated_as_valid
            entity.is_active = is_active
            entity.is_employee_visible = is_employee_visible
            entity.order_index = order_index
        else:
            # Создаем КОПИЮ для владельца, чтобы не дублировать глобальные записи на списке
            db.add(CancellationReason(
                owner_id=user.id,
                code=code,
                title=title,
                requires_document=requires_document,
                treated_as_valid=treated_as_valid,
                is_active=is_active,
                is_employee_visible=is_employee_visible,
                order_index=order_index,
            ))

    await db.commit()
    return RedirectResponse(url="/owner/cancellations", status_code=303)


