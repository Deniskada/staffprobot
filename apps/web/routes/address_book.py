"""API работы с базой адресов (поиск и создание).

Будет использоваться общим компонентом выбора адреса.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.middleware.role_middleware import require_any_role, get_user_id_from_current_user
from core.database.session import get_db_session
from core.logging.logger import logger
from domain.entities.address import Address
from domain.entities.user import UserRole

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.get("/search")
async def search_addresses(
    q: str = Query("", description="Строка поиска по адресу"),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Поиск по базе адресов по подстроке."""
    try:
        query = select(Address).order_by(Address.id.desc()).limit(limit)
        if q:
            like = f"%{q}%"
            query = query.where(Address.full_address.ilike(like))

        result = await session.execute(query)
        addresses: List[Address] = list(result.scalars().all())

        return JSONResponse(
            {
                "success": True,
                "items": [
                    {
                        "id": a.id,
                        "full_address": a.full_address,
                        "city": a.city,
                        "street": a.street,
                        "house": a.house,
                    }
                    for a in addresses
                ],
            }
        )
    except Exception as e:
        logger.error("Error searching addresses", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка поиска адресов"}, status_code=500)


@router.post("/")
async def create_address(
    request: Request,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Создать новый адрес в базе."""
    try:
        payload: Dict[str, Any] = await request.json()

        # При неавторизованном доступе require_any_role вернёт RedirectResponse,
        # в этом случае просто не привязываем user_id к адресу.
        user_id: Optional[int] = None
        if not isinstance(current_user, RedirectResponse):
            user_id = await get_user_id_from_current_user(current_user, session)

        address = Address(
            user_id=user_id,
            country=payload.get("country") or "Россия",
            region=payload.get("region"),
            city=payload.get("city") or "",
            street=payload.get("street"),
            house=payload.get("house"),
            building=payload.get("building"),
            apartment=payload.get("apartment"),
            postal_code=payload.get("postal_code"),
            full_address=payload.get("full_address"),
        )
        session.add(address)
        await session.commit()
        await session.refresh(address)

        return JSONResponse(
            {
                "success": True,
                "address": {
                    "id": address.id,
                    "full_address": address.full_address,
                    "city": address.city,
                    "street": address.street,
                    "house": address.house,
                },
            }
        )
    except Exception as e:
        # Логируем полный стек для диагностики
        logger.exception("Error creating address")
        return JSONResponse({"success": False, "error": "Ошибка создания адреса"}, status_code=500)

