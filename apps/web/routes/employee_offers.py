"""Роуты сотрудника для работы с офертами."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.jinja import templates
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.database.session import get_db_session
from domain.entities.user import User
from domain.entities.contract import Contract, ContractTemplate
from domain.entities.contract_type import ContractType
from domain.entities.application import Application
from sqlalchemy import func

logger = logging.getLogger(__name__)
router = APIRouter()


async def _base_context(current_user: dict, db: AsyncSession, user_id: int) -> dict:
    """Переменные, обязательные для base_employee.html."""
    from apps.web.routes.employee import get_available_interfaces_for_user
    available_interfaces = await get_available_interfaces_for_user(current_user, db)
    apps_result = await db.execute(
        select(func.count(Application.id)).where(Application.applicant_id == user_id)
    )
    return {
        "available_interfaces": available_interfaces,
        "applications_count": apps_result.scalar() or 0,
    }


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

    # Список профилей сотрудника (для выбора / навигации)
    from domain.entities.profile import Profile, IndividualProfile
    profiles_result = await db.execute(
        select(Profile)
        .where(Profile.user_id == user_id, Profile.profile_type == "individual", Profile.is_archived.is_(False))
        .order_by(Profile.is_default.desc(), Profile.id)
    )
    profiles_list = []
    for p in profiles_result.scalars().all():
        ip_r = await db.execute(select(IndividualProfile).where(IndividualProfile.profile_id == p.id))
        ip = ip_r.scalar_one_or_none()
        fio = ""
        if ip:
            fio = " ".join(filter(None, [ip.last_name, ip.first_name, ip.middle_name]))
        profiles_list.append({
            "id": p.id,
            "name": fio or f"Профиль #{p.id}",
            "is_default": p.is_default,
            "is_selected": p.id == validation.get("profile_id"),
        })

    # Загруженные документы (без S3-клиента — просто данные из БД)
    documents = []
    profile_id = validation.get("profile_id")
    if profile_id:
        from domain.entities.profile_document import ProfileDocument
        from shared.services.profile_document_service import DOCUMENT_TYPE_LABELS
        doc_result = await db.execute(
            select(ProfileDocument)
            .where(ProfileDocument.profile_id == profile_id)
            .order_by(ProfileDocument.document_type)
        )
        for d in doc_result.scalars().all():
            documents.append({
                "id": d.id,
                "document_type": d.document_type,
                "label": DOCUMENT_TYPE_LABELS.get(d.document_type, d.document_type),
                "original_filename": d.original_filename,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            })

    ctx = await _base_context(current_user, db, user_id)
    return templates.TemplateResponse(
        "employee/offers/accept.html",
        {
            "request": request,
            "current_user": current_user,
            "contract": contract_data,
            "validation": validation,
            "documents": documents,
            "profiles": profiles_list,
            "title": f"Оферта — {contract_data['title']}",
            **ctx,
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
    from telegram import Bot
    from core.config.settings import settings as app_settings

    telegram_id = current_user.get("telegram_id") or current_user.get("id")
    bot = Bot(token=app_settings.telegram_bot_token)
    pep_service = PepService(channel=TelegramPepChannel(bot=bot))
    result = await pep_service.initiate_signing(
        user_id=user_id,
        telegram_id=telegram_id,
        contract_id=contract_id,
    )
    if result["status"] != "sent":
        raise HTTPException(status_code=500, detail="Не удалось отправить код")

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
    from shared.services.pep_service import PepService
    pep_service = PepService()
    client_ip = request.client.host if request.client else None
    otp_result = await pep_service.verify_otp(
        user_id=user_id,
        contract_id=contract_id,
        code=otp_code,
        client_ip=client_ip,
    )

    if not otp_result.get("valid"):
        raise HTTPException(
            status_code=400,
            detail=otp_result.get("status", "Неверный код подтверждения"),
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

    # Отправляем уведомление владельцу
    try:
        from shared.services.notification_service import NotificationService
        from domain.entities.notification import NotificationType, NotificationChannel

        ns = NotificationService()
        contract_data = await offer_service.get_contract_for_acceptance(db, contract_id, user_id)
        if contract_data and contract_data.get("owner_id"):
            emp_name = employee_details.get("employee_fio", "Сотрудник")
            await ns.create_notification(
                user_id=contract_data["owner_id"],
                type=NotificationType.OFFER_ACCEPTED,
                channel=NotificationChannel.TELEGRAM,
                title="Оферта принята",
                message=f"Сотрудник {emp_name} принял оферту «{contract_data.get('title', '')}».",
                data={
                    "contract_id": contract_id,
                    "employee_name": emp_name,
                },
            )
    except Exception as e:
        logger.error(f"Failed to send offer acceptance notification: {e}", exc_info=True)

    return {"status": "accepted", "contract_id": contract_id}


# ─── Список оферт ─────────────────────────────────────────────

@router.get("/offers", response_class=HTMLResponse)
async def offer_list_page(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """Страница «Мои договоры» — оферты (pending / active / rejected)."""
    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await _get_user_id(current_user, db)

    stmt = (
        select(Contract, ContractTemplate)
        .outerjoin(ContractTemplate, Contract.template_id == ContractTemplate.id)
        .where(Contract.employee_id == user_id)
        .order_by(Contract.created_at.desc())
    )
    rows = await db.execute(stmt)
    contracts = []
    for contract, tmpl in rows.all():
        is_offer = False
        if tmpl and tmpl.contract_type_id:
            ct = await db.execute(select(ContractType).where(ContractType.id == tmpl.contract_type_id))
            ct_obj = ct.scalar_one_or_none()
            is_offer = ct_obj and ct_obj.code == "offer"
        if not is_offer and contract.status == "pending_acceptance":
            is_offer = True

        contracts.append({
            "id": contract.id,
            "title": contract.title,
            "contract_number": contract.contract_number,
            "status": contract.status,
            "is_offer": is_offer,
            "start_date": contract.start_date,
            "signed_at": contract.signed_at,
            "created_at": contract.created_at,
            "template_name": tmpl.name if tmpl else None,
        })

    ctx = await _base_context(current_user, db, user_id)
    return templates.TemplateResponse(
        "employee/offers/list.html",
        {
            "request": request,
            "current_user": current_user,
            "contracts": contracts,
            "title": "Мои договоры",
            **ctx,
        },
    )


# ─── Отказ от оферты ──────────────────────────────────────────

@router.post("/offers/{contract_id}/reject", response_class=JSONResponse)
async def offer_reject(
    request: Request,
    contract_id: int,
    reason: str = Form(...),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """API: отказ от оферты с указанием причины."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    offer_service = OfferService()
    result = await offer_service.reject_offer(db, contract_id, user_id, reason.strip())

    # Уведомление собственнику
    try:
        from shared.services.notification_service import NotificationService
        from domain.entities.notification import NotificationType
        from core.database.session import get_async_session

        async with get_async_session() as notify_session:
            ns = NotificationService(notify_session)
            await ns.create_notification(
                user_id=result["owner_id"],
                notification_type=NotificationType.OFFER_REJECTED,
                data={
                    "contract_id": contract_id,
                    "employee_name": result.get("employee_name", ""),
                    "reason": reason.strip(),
                },
            )
    except Exception as e:
        logger.error(f"Failed to send offer rejection notification: {e}")

    return {"status": "rejected", "contract_id": contract_id}


# ─── Загрузка документов профиля ──────────────────────────────

@router.post("/documents/upload", response_class=JSONResponse)
async def upload_profile_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """Загрузить скан документа (паспорт, ИНН, СНИЛС)."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    offer_service = OfferService()
    validation = await offer_service.validate_employee_profile(db, user_id)
    profile_id = validation.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Сначала создайте профиль физлица")

    content = await file.read()

    from shared.services.profile_document_service import ProfileDocumentService
    doc_service = ProfileDocumentService()
    try:
        result = await doc_service.upload_document(
            session=db,
            profile_id=profile_id,
            document_type=document_type,
            file_content=content,
            filename=file.filename or "scan.jpg",
            mime_type=file.content_type or "application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Логируем загрузку документа для всех pending-контрактов сотрудника
    try:
        from shared.services.contract_history_service import log_contract_event
        from domain.entities.contract_history import ContractChangeType
        pending = await db.execute(
            select(Contract.id).where(
                Contract.employee_id == user_id,
                Contract.status == "pending_acceptance",
            )
        )
        for (cid,) in pending.fetchall():
            await log_contract_event(
                db, cid, ContractChangeType.DOCUMENT_UPLOADED,
                changed_by=user_id,
                details={"document_type": document_type, "filename": file.filename},
            )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to log document upload event: {e}")

    return result


@router.get("/documents", response_class=JSONResponse)
async def list_profile_documents(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """Получить список загруженных документов текущего сотрудника."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    validation = await OfferService().validate_employee_profile(db, user_id)
    profile_id = validation.get("profile_id")
    if not profile_id:
        return []

    from shared.services.profile_document_service import ProfileDocumentService
    return await ProfileDocumentService().get_documents(db, profile_id)


@router.delete("/documents/{doc_id}", response_class=JSONResponse)
async def delete_profile_document(
    request: Request,
    doc_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
):
    """Удалить скан документа."""
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Не авторизован")

    user_id = await _get_user_id(current_user, db)

    from shared.services.offer_service import OfferService
    validation = await OfferService().validate_employee_profile(db, user_id)
    profile_id = validation.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Профиль не найден")

    from shared.services.profile_document_service import ProfileDocumentService
    ok = await ProfileDocumentService().delete_document(db, doc_id, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return {"status": "deleted"}
