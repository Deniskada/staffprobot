"""Роуты владельца для управления справочником товаров."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.user import User
from shared.services.product_service import ProductService

router = APIRouter()


async def _get_db_user_id(current_user, session: AsyncSession) -> int | None:
    from sqlalchemy import select as sql_select
    from domain.entities.user import User as UserEntity
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        res = await session.execute(sql_select(UserEntity).where(UserEntity.telegram_id == telegram_id))
        u = res.scalar_one_or_none()
        return u.id if u else None
    return current_user.id


async def _get_owner_template_context(owner_id: int, session: AsyncSession):
    from apps.web.routes.owner import get_owner_context
    return await get_owner_context(owner_id, session)


@router.get("/owner/products")
async def owner_products_list(
    request: Request,
    show_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session),
):
    owner_id = await _get_db_user_id(current_user, session)
    svc = ProductService(session)
    products = await svc.list_products(owner_id, include_inactive=show_inactive)
    owner_context = await _get_owner_template_context(owner_id, session)
    return templates.TemplateResponse(
        "owner/products/list.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": owner_context.get("available_interfaces", []),
            "new_applications_count": owner_context.get("new_applications_count", 0),
            "products": products,
            "show_inactive": show_inactive,
        },
    )


@router.post("/owner/products")
async def owner_products_save(
    request: Request,
    name: str = Form(...),
    unit: str = Form("шт."),
    price: str = Form("0"),
    product_id: int = Form(None),
    action: str = Form("save"),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session),
):
    owner_id = await _get_db_user_id(current_user, session)
    svc = ProductService(session)

    if action == "deactivate" and product_id:
        await svc.deactivate_product(product_id)
    elif action == "activate" and product_id:
        await svc.activate_product(product_id)
    elif product_id:
        parsed_price = float(price) if price else 0
        await svc.update_product(product_id, name=name, unit=unit, price=parsed_price)
    else:
        parsed_price = float(price) if price else 0
        await svc.create_product(owner_id, name=name, unit=unit, price=parsed_price)

    return RedirectResponse(url="/owner/products", status_code=303)
