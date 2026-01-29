"""Shared API для управления пользовательскими профилями (ФЛ, ИП, ЮЛ)."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.middleware.role_middleware import require_any_role, get_user_id_from_current_user
from apps.web.dependencies import get_current_user_dependency
from core.database.session import get_db_session
from core.logging.logger import logger
from domain.entities.user import UserRole
from shared.services.profile_service import ProfileService
from shared.services.kyc_service import KycService

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _base_and_details_from_payload(payload: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Разделяет базовые поля и детали профиля."""
    base_keys = {"profile_type", "display_name", "is_default"}
    base = {k: v for k, v in payload.items() if k in base_keys}
    details = {k: v for k, v in payload.items() if k not in base_keys}
    return base, details


def _validate_required_details(profile_type: str, details: Dict[str, Any]) -> None:
    """
    Простая серверная валидация обязательных полей, чтобы не падать 500‑кой
    на NOT NULL в БД.
    """
    pt = profile_type
    if pt == "individual":
        required = ["last_name", "first_name", "citizenship"]
    elif pt == "legal":
        required = ["full_name"]
    elif pt == "sole_proprietor":
        required = ["last_name", "first_name"]
    else:
        raise HTTPException(status_code=400, detail="Неизвестный тип профиля")

    missing = [f for f in required if not details.get(f)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Не заполнены обязательные поля: {', '.join(missing)}",
        )


@router.get("/")
async def list_profiles(
    request: Request,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Список профилей текущего пользователя."""
    try:
        # require_any_role может вернуть RedirectResponse для неавторизованных запросов
        from fastapi.responses import RedirectResponse

        if isinstance(current_user, RedirectResponse):
            return current_user

        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        service = ProfileService()
        profiles = await service.list_user_profiles(session, user_id)
        return JSONResponse({"success": True, "profiles": profiles})
    except HTTPException:
        raise
    except Exception:
        # Логируем полный стек для диагностики
        logger.exception("Error listing profiles")
        return JSONResponse({"success": False, "error": "Ошибка получения профилей"}, status_code=500)


@router.get("/{profile_id}")
async def get_profile(
    profile_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Получить один профиль по ID."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        service = ProfileService()
        dto = await service.get_profile_dto(session, profile_id, user_id)
        if not dto:
            return JSONResponse({"success": False, "error": "Профиль не найден"}, status_code=404)
        return JSONResponse({"success": True, "profile": dto})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting profile", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка получения профиля"}, status_code=500)


@router.post("/")
async def create_profile(
    request: Request,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Создать новый профиль."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        payload = await request.json()
        base, details = _base_and_details_from_payload(payload)
        if "profile_type" not in base or "display_name" not in base:
            raise HTTPException(status_code=400, detail="profile_type и display_name обязательны")

        _validate_required_details(base["profile_type"], details)

        service = ProfileService()
        dto = await service.create_profile(session, user_id, base, details)
        return JSONResponse({"success": True, "profile": dto})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error creating profile", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка создания профиля"}, status_code=500)


@router.put("/{profile_id}")
async def update_profile(
    profile_id: int,
    request: Request,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Обновить профиль."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        payload = await request.json()
        base, details = _base_and_details_from_payload(payload)

        service = ProfileService()
        dto = await service.update_profile(session, profile_id, user_id, base, details)
        if not dto:
            return JSONResponse({"success": False, "error": "Профиль не найден"}, status_code=404)
        return JSONResponse({"success": True, "profile": dto})
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception("Error updating profile")
        return JSONResponse({"success": False, "error": "Ошибка обновления профиля"}, status_code=500)


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Архивировать профиль."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        service = ProfileService()
        ok = await service.delete_profile(session, profile_id, user_id)
        if not ok:
            return JSONResponse({"success": False, "error": "Профиль не найден"}, status_code=404)
        return JSONResponse({"success": True})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error deleting profile", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка удаления профиля"}, status_code=500)


@router.post("/{profile_id}/set-default")
async def set_default_profile(
    profile_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Сделать профиль профилем по умолчанию."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        service = ProfileService()
        ok = await service.set_default_profile(session, profile_id, user_id)
        if not ok:
            return JSONResponse({"success": False, "error": "Профиль не найден"}, status_code=404)
        return JSONResponse({"success": True})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error setting default profile", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка установки профиля по умолчанию"}, status_code=500)


@router.post("/{profile_id}/kyc/start")
async def start_kyc_verification(
    profile_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """Инициировать KYC‑верификацию профиля через провайдера (госуслуги)."""
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        service = KycService()
        result = await service.start_verification(session, profile_id, user_id)
        return JSONResponse({"success": True, "kyc": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=404)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting KYC", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка запуска KYC‑верификации"}, status_code=500)


@router.post("/{profile_id}/kyc/mark-verified")
async def mark_profile_verified(
    profile_id: int,
    request: Request,
    current_user=Depends(require_any_role([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Временный endpoint для пометки профиля как подтвержденного.

    В боевой интеграции будет заменён callback'ом от провайдера госуслуг.
    """
    try:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        payload = {}
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        service = KycService()
        result = await service.mark_verified(session, profile_id, user_id, provider_payload=payload)
        return JSONResponse({"success": True, "kyc": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=404)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error marking profile verified", error=str(e))
        return JSONResponse({"success": False, "error": "Ошибка подтверждения профиля"}, status_code=500)

