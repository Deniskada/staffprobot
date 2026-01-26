"\"\"\"Shared страница отмены смен для всех ролей.\"\"\""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple, Iterable, Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.web.jinja import templates
from apps.web.middleware.role_middleware import require_any_role, get_user_id_from_current_user
from apps.web.utils.timezone_utils import WebTimezoneHelper
from core.cache.redis_cache import cache
from core.database.session import get_db_session
from core.logging.logger import logger
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.user import UserRole
from shared.services.cancellation_policy_service import CancellationPolicyService
from shared.services.manager_permission_service import ManagerPermissionService
from shared.services.role_based_login_service import RoleBasedLoginService
from shared.services.shift_cancellation_service import ShiftCancellationService
from shared.services.system_features_service import SystemFeaturesService
from apps.web.utils.applications_utils import get_new_applications_count
from domain.entities.contract import Contract
from domain.entities.application import Application


router = APIRouter()

ALLOWED_ROLES = [UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE, UserRole.SUPERADMIN]

ROLE_BASE_TEMPLATE = {
    "owner": "owner/base_owner.html",
    "manager": "manager/base_manager.html",
    "employee": "employee/base_employee.html",
    "superadmin": "owner/base_owner.html",
}

ROLE_DEFAULT_RETURN = {
    "owner": "/owner/calendar",
    "manager": "/manager/calendar",
    "employee": "/employee/calendar",
    "superadmin": "/owner/calendar",
}

timezone_helper = WebTimezoneHelper()


def _normalize_roles(raw_roles: Iterable) -> List[str]:
    normalized: List[str] = []
    for role in raw_roles or []:
        if hasattr(role, "value"):
            normalized.append(role.value.lower())
        elif isinstance(role, str):
            normalized.append(role.lower())
    return normalized


def _determine_actor_role(roles: List[str]) -> str:
    priority = ["owner", "manager", "employee", "superadmin"]
    for candidate in priority:
        if candidate in roles:
            return candidate
    return roles[0] if roles else "employee"


def _sanitize_return_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url)
    # Отбрасываем схему и домен, оставляем только путь и query
    sanitized = parsed._replace(scheme="", netloc="")
    # Если путь пустой, добавляем '/'
    if not sanitized.path:
        sanitized = sanitized._replace(path="/")
    return urlunparse(sanitized)


def _append_query_params(url: str, params: Dict[str, Optional[int]]) -> str:
    parsed = urlparse(url)
    existing_params = dict(parse_qsl(parsed.query))
    for key, value in params.items():
        if value is not None:
            existing_params[key] = str(value)
    new_query = urlencode(existing_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


async def _load_accessible_schedules(
    session: AsyncSession,
    schedule_ids: List[int],
    actor_role: str,
    roles: List[str],
    internal_user_id: Optional[int],
) -> Tuple[List[ShiftSchedule], int]:
    """Получить список расписаний, доступных пользователю."""
    if not schedule_ids:
        raise HTTPException(status_code=400, detail="Не выбраны смены для отмены")

    query = (
        select(ShiftSchedule)
        .options(
            selectinload(ShiftSchedule.object),
            selectinload(ShiftSchedule.user),
        )
        .where(ShiftSchedule.id.in_(schedule_ids))
    )
    result = await session.execute(query)
    schedule_map = {schedule.id: schedule for schedule in result.scalars().all()}

    missing_ids = [sid for sid in schedule_ids if sid not in schedule_map]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Смены {missing_ids} не найдены")

    manager_object_ids: Optional[set[int]] = None
    if actor_role == "manager" and internal_user_id:
        permission_service = ManagerPermissionService(session)
        accessible_objects = await permission_service.get_user_accessible_objects(internal_user_id)
        manager_object_ids = {obj.id for obj in accessible_objects}

    accessible: List[ShiftSchedule] = []
    owner_ids = set()

    for schedule_id in schedule_ids:
        schedule = schedule_map[schedule_id]
        if schedule.status != "planned":
            raise HTTPException(
                status_code=400,
                detail=f"Смену с ID {schedule.id} не удалось отменить: статус {schedule.status}",
            )

        object_owner_id = schedule.object.owner_id if schedule.object else None
        has_access = False

        if "superadmin" in roles:
            has_access = True
        elif actor_role == "owner" and internal_user_id:
            has_access = object_owner_id == internal_user_id
        elif actor_role == "manager" and manager_object_ids is not None:
            has_access = schedule.object_id in manager_object_ids
        elif actor_role == "employee" and internal_user_id:
            has_access = schedule.user_id == internal_user_id

        if not has_access:
            raise HTTPException(status_code=403, detail=f"Нет доступа к смене {schedule.id}")

        if object_owner_id:
            owner_ids.add(object_owner_id)

        accessible.append(schedule)

    if not accessible:
        raise HTTPException(status_code=404, detail="Смены не найдены")

    if len(owner_ids) > 1:
        raise HTTPException(
            status_code=400,
            detail="Нельзя отменять смены разных владельцев за один раз",
        )

    owner_id = next(iter(owner_ids)) if owner_ids else None
    if owner_id is None:
        raise HTTPException(status_code=400, detail="Не удалось определить владельца смены")

    return accessible, owner_id


def _build_shift_payload(schedule: ShiftSchedule) -> Dict[str, Any]:
    """Подготовить данные для отображения смены на странице."""
    timezone = schedule.object.timezone if schedule.object and schedule.object.timezone else "Europe/Moscow"
    start_label = timezone_helper.format_datetime_with_timezone(schedule.planned_start, timezone, "%d.%m.%Y %H:%M")
    end_label = timezone_helper.format_datetime_with_timezone(schedule.planned_end, timezone, "%d.%m.%Y %H:%M")

    employee_name = "Не назначен"
    if schedule.user:
        parts = [schedule.user.last_name or "", schedule.user.first_name or ""]
        employee_name = " ".join(p for p in parts if p).strip() or schedule.user.username or "Сотрудник"

    return {
        "schedule_id": schedule.id,
        "object_name": schedule.object.name if schedule.object else "Неизвестный объект",
        "employee_name": employee_name,
        "start_label": start_label,
        "end_label": end_label,
        "status": schedule.status,
        "timezone": timezone,
        "raw_start": schedule.planned_start,
        "raw_end": schedule.planned_end,
    }


def _convert_reason(reason) -> Dict[str, Any]:
    """Привести причину к словарю для шаблона."""
    return {
        "code": reason.code,
        "title": reason.title,
        "is_active": bool(reason.is_active),
        "is_employee_visible": bool(reason.is_employee_visible),
        "requires_document": bool(reason.requires_document),
        "treated_as_valid": bool(reason.treated_as_valid),
        "order_index": reason.order_index or 0,
    }


@router.api_route("/form", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def show_cancellation_form(
    request: Request,
    shift_type: str = Query("schedule"),
    shift_ids: str = Query(..., description="Спиcок ID смен через запятую"),
    return_to: Optional[str] = Query(None),
    caller: Optional[str] = Query(None),
    current_user: dict = Depends(require_any_role(ALLOWED_ROLES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Страница выбора причины отмены смен."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    if request.method == "HEAD":
        return HTMLResponse(status_code=200)

    # Сохраняем пользователя в request.state для базовых шаблонов
    request.state.current_user = current_user
    if not hasattr(request.state, "enabled_features"):
        request.state.enabled_features = []

    if shift_type != "schedule":
        raise HTTPException(status_code=400, detail="Поддерживаются только плановые смены")

    id_list: List[int] = []
    for raw in shift_ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("schedule_"):
            raw = raw.replace("schedule_", "")
        try:
            id_list.append(int(raw))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Некорректный идентификатор смены: {raw}")

    roles = _normalize_roles(current_user.get("roles", []))
    actor_role = _determine_actor_role(roles)

    internal_user_id = await get_user_id_from_current_user(current_user, db)
    schedules, owner_id = await _load_accessible_schedules(
        db,
        id_list,
        actor_role,
        roles,
        internal_user_id,
    )

    only_visible = actor_role == "employee"
    reasons = await CancellationPolicyService.get_owner_reasons(
        db,
        owner_id,
        only_visible=only_visible,
        only_active=True,
    )

    if not reasons:
        raise HTTPException(status_code=400, detail="Для владельца не настроены причины отмены")

    # Обновляем enabled_features вручную (middleware работает только для /owner/*)
    enabled_features: List[str] = []
    features_target_id = owner_id or internal_user_id
    if features_target_id:
        try:
            features_service = SystemFeaturesService()
            enabled_features = await features_service.get_enabled_features(db, features_target_id) or []
        except Exception as features_error:
            logger.warning(
                "Не удалось получить список функций для shared отмены",
                error=str(features_error),
                owner_id=owner_id,
                user_id=internal_user_id,
            )
    request.state.enabled_features = enabled_features

    # Доступные интерфейсы для переключателя
    available_interfaces: List[Dict[str, Any]] = []
    if internal_user_id:
        try:
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(internal_user_id)
        except Exception as interface_error:
            logger.warning(
                "Не удалось получить список интерфейсов для shared отмены",
                error=str(interface_error),
                user_id=internal_user_id,
            )

    # Счётчик новых откликов для владельца/управляющего (бейджи в меню)
    new_applications_count: Optional[int] = None
    try:
        if actor_role in ("owner", "superadmin") and features_target_id:
            new_applications_count = await get_new_applications_count(features_target_id, db, "owner")
        elif actor_role == "manager" and internal_user_id:
            new_applications_count = await get_new_applications_count(internal_user_id, db, "manager")
    except Exception as applications_error:
        logger.warning(
            "Не удалось получить количество новых откликов",
            error=str(applications_error),
            user_id=internal_user_id,
            actor_role=actor_role,
        )

    manager_can_manage_payroll: Optional[bool] = None
    if actor_role == "manager" and internal_user_id:
        manager_can_manage_payroll = False
        contracts_query = select(Contract).where(
            Contract.employee_id == internal_user_id,
            Contract.is_manager.is_(True),
            Contract.is_active.is_(True),
            Contract.status == "active",
        )
        contracts_result = await db.execute(contracts_query)
        for contract in contracts_result.scalars().all():
            permissions = contract.manager_permissions or {}
            if permissions.get("can_manage_payroll"):
                manager_can_manage_payroll = True
                break

    employee_applications_count: Optional[int] = None
    if actor_role == "employee" and internal_user_id:
        applications_query = select(func.count(Application.id)).where(
            Application.applicant_id == internal_user_id
        )
        applications_result = await db.execute(applications_query)
        employee_applications_count = applications_result.scalar() or 0

    reason_items = [_convert_reason(reason) for reason in reasons]
    shift_items = [_build_shift_payload(schedule) for schedule in schedules]

    base_template = ROLE_BASE_TEMPLATE.get(actor_role, "owner/base_owner.html")
    sanitized_return = _sanitize_return_url(return_to) or ROLE_DEFAULT_RETURN.get(actor_role, "/")

    return templates.TemplateResponse(
        "shared/cancellations/form.html",
        {
            "request": request,
            "base_template": base_template,
            "role": actor_role,
            "shift_type": shift_type,
            "shift_ids": ",".join(str(s.id) for s in schedules),
            "shifts": shift_items,
            "reasons": reason_items,
            "return_to": sanitized_return,
            "caller": caller,
            "owner_id": owner_id,
            "current_user": current_user,
            "available_interfaces": available_interfaces,
            "new_applications_count": new_applications_count,
            "enabled_features": enabled_features,
            "can_manage_payroll": manager_can_manage_payroll,
            "applications_count": employee_applications_count,
        },
    )


@router.post("/submit")
async def submit_cancellation_form(
    request: Request,
    shift_type: str = Form(...),
    shift_ids: str = Form(...),
    reason: str = Form(...),
    notes: Optional[str] = Form(None),
    document_description: Optional[str] = Form(None),
    return_to: Optional[str] = Form(None),
    caller: Optional[str] = Form(None),
    media_files: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(require_any_role(ALLOWED_ROLES)),
    db: AsyncSession = Depends(get_db_session),
):
    """Обработка формы отмены смен."""
    logger.info(
        "Shared cancellation POST received",
        shift_type=shift_type,
        shift_ids=shift_ids,
        has_media=bool(media_files),
    )
    
    if isinstance(current_user, RedirectResponse):
        return current_user

    if shift_type != "schedule":
        raise HTTPException(status_code=400, detail="Поддерживаются только плановые смены")

    schedule_ids: List[int] = []
    for raw in shift_ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("schedule_"):
            raw = raw.replace("schedule_", "")
        try:
            schedule_ids.append(int(raw))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Некорректный идентификатор смены: {raw}")

    if not schedule_ids:
        raise HTTPException(status_code=400, detail="Не выбраны смены для отмены")

    roles = _normalize_roles(current_user.get("roles", []))
    actor_role = _determine_actor_role(roles)

    internal_user_id = await get_user_id_from_current_user(current_user, db)
    schedules, owner_id = await _load_accessible_schedules(
        db,
        schedule_ids,
        actor_role,
        roles,
        internal_user_id,
    )

    reason_map = await CancellationPolicyService.get_reason_map(
        db,
        owner_id,
        include_inactive=False,
        include_hidden=actor_role != "employee",
    )

    reason_obj = reason_map.get(reason)
    if not reason_obj:
        raise HTTPException(status_code=400, detail="Выбрана недоступная причина отмены")

    if reason_obj.requires_document and not document_description:
        raise HTTPException(status_code=400, detail="Для выбранной причины требуется описание документа")

    logger.info(
        "Shared cancellation submit started",
        owner_id=owner_id,
        schedule_ids=schedule_ids,
        has_media=bool(media_files),
    )

    media_list: List[Dict[str, Any]] = []
    try:
        if not owner_id:
            logger.warning(
                "Shared cancellation: owner_id is None, skipping media upload",
                schedule_ids=schedule_ids,
            )
        else:
            from core.config.settings import settings
            from shared.services.owner_media_storage_service import get_storage_mode

            mode = await get_storage_mode(db, owner_id, "cancellations")
            use_storage = mode in ("storage", "both")
            provider = (settings.media_storage_provider or "").strip().lower()
            files_list: List[UploadFile] = (
                list(media_files) if isinstance(media_files, (list, tuple)) else ([media_files] if media_files else [])
            )
            file_count = sum(1 for uf in files_list if getattr(uf, "filename", None))

            logger.info(
                "Shared cancellation media check",
                owner_id=owner_id,
                mode=mode,
                provider=provider,
                use_storage=use_storage,
                file_count=file_count,
            )

            if not use_storage:
                logger.info(
                    "Shared cancellation: skip S3 upload (use_storage=False)",
                    mode=mode,
                )
            elif provider not in ("minio", "s3"):
                logger.info(
                    "Shared cancellation: skip S3 upload (provider not minio/s3)",
                    provider=provider,
                )
            elif not file_count:
                logger.info("Shared cancellation: skip S3 upload (no media_files)")
            else:
                from shared.services.media_storage import get_media_storage_client

                storage = get_media_storage_client()
                folder = f"cancellations/{schedules[0].id}"
                for uf in files_list:
                    filename = getattr(uf, "filename", None)
                    if not filename:
                        continue
                    # Важно: файл может быть уже прочитан, нужно проверить позицию
                    try:
                        uf.file.seek(0)  # Перематываем на начало
                    except (AttributeError, OSError):
                        pass  # Если нет метода seek, продолжаем
                    raw = await uf.read()
                    if not raw:
                        logger.warning("Shared cancellation: skipping empty file", filename=filename)
                        continue
                    content_type = getattr(uf, "content_type", None) or "application/octet-stream"
                    m = await storage.upload(raw, uf.filename, content_type, folder)
                    media_list.append({
                        "key": m.key,
                        "url": m.url,
                        "type": m.type,
                        "size": m.size,
                        "mime_type": m.mime_type,
                    })
                    logger.info(
                        "Shared cancellation: uploaded to S3",
                        key=m.key,
                        folder=folder,
                    )
    except Exception as e:
        logger.exception(
            "Shared cancellation media upload failed",
            error=str(e),
            owner_id=owner_id,
        )

    cancellation_service = ShiftCancellationService(db)
    success_ids: List[int] = []
    error_messages: List[str] = []

    for schedule in schedules:
        result = await cancellation_service.cancel_shift(
            shift_schedule_id=schedule.id,
            cancelled_by_user_id=internal_user_id if internal_user_id else schedule.user_id,
            cancelled_by_type=actor_role,
            cancellation_reason=reason,
            reason_notes=notes,
            document_description=document_description,
            actor_role=actor_role,
            source="web",
            extra_payload={
                "caller": caller,
                "interface": "shared_cancellation_form",
            },
            media=media_list if media_list else None,
        )
        if result.get("success"):
            success_ids.append(schedule.id)
        else:
            message = result.get("message") or result.get("error") or "Не удалось отменить смену"
            error_messages.append(f"Смена {schedule.id}: {message}")

    if success_ids:
        try:
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")
        except Exception as cache_error:
            logger.warning(f"Не удалось очистить кэш календаря: {cache_error}")

    sanitized_return = _sanitize_return_url(return_to) or ROLE_DEFAULT_RETURN.get(actor_role, "/")

    if success_ids and sanitized_return:
        redirect_url = _append_query_params(
            sanitized_return,
            {
                "cancel_success": len(success_ids),
                "cancel_errors": len(error_messages) if error_messages else None,
            },
        )
        return RedirectResponse(url=redirect_url, status_code=303)

    # Если нет успешных отмен, отображаем форму снова с ошибками
    if not success_ids:
        base_template = ROLE_BASE_TEMPLATE.get(actor_role, "owner/base_owner.html")
        reason_items = [_convert_reason(r) for r in reason_map.values() if r.is_active]
        shift_items = [_build_shift_payload(schedule) for schedule in schedules]

        return templates.TemplateResponse(
            "shared/cancellations/form.html",
            {
                "request": request,
                "base_template": base_template,
                "role": actor_role,
                "shift_type": shift_type,
                "shift_ids": ",".join(str(s) for s in schedule_ids),
                "shifts": shift_items,
                "reasons": sorted(reason_items, key=lambda item: (item["order_index"], item["title"])),
                "return_to": sanitized_return,
                "caller": caller,
                "owner_id": owner_id,
                "error_messages": error_messages or ["Не удалось отменить выбранные смены."],
                "selected_reason": reason,
                "notes": notes,
                "document_description": document_description,
            },
            status_code=400,
        )

    # Fallback на redirect без параметров
    return RedirectResponse(url=sanitized_return, status_code=303)


@router.get("/reasons", response_class=JSONResponse)
async def list_cancellation_reasons(
    owner_id: int = Query(...),
    include_hidden: bool = Query(False),
    current_user: dict = Depends(require_any_role(ALLOWED_ROLES)),
    db: AsyncSession = Depends(get_db_session),
):
    """API: список причин отмен для владельца (используется ботом/вебом)."""
    roles = _normalize_roles(current_user.get("roles", []))
    actor_role = _determine_actor_role(roles)
    include_hidden = include_hidden or actor_role != "employee"

    async with db.begin():
        reasons = await CancellationPolicyService.get_owner_reasons(
            db,
            owner_id,
            only_visible=not include_hidden,
            only_active=True,
        )

    return [
        {
            "code": reason.code,
            "title": reason.title,
            "requires_document": bool(reason.requires_document),
            "treated_as_valid": bool(reason.treated_as_valid),
            "is_employee_visible": bool(reason.is_employee_visible),
        }
        for reason in reasons
    ]

