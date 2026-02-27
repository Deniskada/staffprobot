"""Роуты сотрудника для работы с офертами."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.jinja import templates
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.database.session import get_db_session
from domain.entities.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_user_id(current_user: dict, session: AsyncSession) -> int:
    """Получить внутренний user_id из current_user."""
    telegram_id = current_user.get("telegram_id") or current_user.get("id")
    result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    user_id = result.scalar_one_or_none()
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user_id


@router.get("/offers/{contract_id}", response_class=HTMLResponse)
async def offer_accept_page(
    request: Request,
    contract_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """Страница просмотра и акцепта оферты."""
    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    offer_service = OfferService()

    contract_data = await offer_service.get_contract_for_acceptance(db, contract_id, user_id)
    if not contract_data:
        raise HTTPException(status_code=404, detail="Оферта не найдена")

    if not contract_data["is_offer"]:
        raise HTTPException(status_code=400, detail="Это не оферта")

    # Проверяем заполненность реквизитов
    validation = await offer_service.validate_employee_profile(db, user_id)

    return templates.TemplateResponse(
        "employee/offers/accept.html",
        {
            "request": request,
            "current_user": current_user,
            "contract": contract_data,
            "validation": validation,
            "title": f"Оферта — {contract_data['title']}",
        },
    )


@router.post("/offers/{contract_id}/validate", response_class=JSONResponse)
async def offer_validate_profile(
    request: Request,
    contract_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """API: проверить заполненность реквизитов перед подписанием."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    offer_service = OfferService()
    validation = await offer_service.validate_employee_profile(db, user_id)
    return validation


@router.post("/offers/{contract_id}/request-otp", response_class=JSONResponse)
async def offer_request_otp(
    request: Request,
    contract_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """API: запросить OTP-код для подписания оферты."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    offer_service = OfferService()

    # Проверяем, что это оферта и она принадлежит сотруднику
    contract_data = await offer_service.get_contract_for_acceptance(db, contract_id, user_id)
    if not contract_data:
        raise HTTPException(status_code=404, detail="Оферта не найдена")

    if contract_data["status"] != "pending_acceptance":
        raise HTTPException(status_code=400, detail="Оферта уже обработана")

    # Проверяем заполненность реквизитов
    validation = await offer_service.validate_employee_profile(db, user_id)
    if not validation["complete"]:
        raise HTTPException(status_code=422, detail="Не все реквизиты заполнены")

    # Отправляем OTP через Telegram
    from shared.services.pep_service import PepService, TelegramPepChannel
    telegram_id = current_user.get("telegram_id") or current_user.get("id")
    pep_service = PepService(channel=TelegramPepChannel())
    await pep_service.send_otp(
        user_identifier=str(telegram_id),
        purpose=f"offer_accept:{contract_id}",
    )

    return {"status": "sent", "channel": "telegram"}


@router.post("/offers/{contract_id}/accept", response_class=JSONResponse)
async def offer_accept(
    request: Request,
    contract_id: int,
    otp_code: str = Form(...),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """API: акцепт оферты — проверить OTP и подписать."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)
    telegram_id = current_user.get("telegram_id") or current_user.get("id")

    from shared.services.offer_service import OfferService
    offer_service = OfferService()

    # Проверяем заполненность реквизитов
    validation = await offer_service.validate_employee_profile(db, user_id)
    if not validation["complete"]:
        raise HTTPException(status_code=422, detail="Не все реквизиты заполнены")

    # Верифицируем OTP
    from shared.services.pep_service import PepService, TelegramPepChannel
    pep_service = PepService(channel=TelegramPepChannel())
    otp_result = await pep_service.verify_otp(
        user_identifier=str(telegram_id),
        purpose=f"offer_accept:{contract_id}",
        code=otp_code,
    )

    if not otp_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail=otp_result.get("error", "Неверный код подтверждения"),
        )

    # Собираем реквизиты сотрудника
    employee_details = await offer_service.get_employee_details_for_contract(db, user_id)

    # Определяем IP
    client_ip = request.client.host if request.client else "unknown"

    pep_metadata = {
        "channel": "telegram",
        "otp_hash": otp_result.get("otp_hash", ""),
        "signed_ip": client_ip,
        "signed_at": otp_result.get("verified_at", ""),
    }

    # Акцепт
    try:
        result = await offer_service.accept_offer(
            session=db,
            contract_id=contract_id,
            employee_user_id=user_id,
            pep_metadata=pep_metadata,
            employee_details=employee_details,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Отправляем уведомления
    try:
        from shared.services.notification_service import NotificationService
        from domain.entities.notification import NotificationType
        from core.database.session import get_async_session

        async with get_async_session() as notify_session:
            ns = NotificationService(notify_session)
            # Уведомление владельцу
            contract_data = await offer_service.get_contract_for_acceptance(db, contract_id, user_id)
            if contract_data and contract_data.get("owner_id"):
                await ns.create_notification(
                    user_id=contract_data["owner_id"],
                    notification_type=NotificationType.OFFER_ACCEPTED,
                    data={
                        "contract_id": contract_id,
                        "employee_name": employee_details.get("employee_fio", ""),
                    },
                )
    except Exception as e:
        logger.error(f"Failed to send offer acceptance notification: {e}")

    return {"status": "accepted", "contract_id": contract_id}
