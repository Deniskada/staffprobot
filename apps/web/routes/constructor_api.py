"""API конструктора шаблонов договоров (owner)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db_session
from apps.web.middleware.role_middleware import require_any_role, get_user_id_from_current_user
from apps.web.services.constructor_service import ConstructorService
from core.logging.logger import logger
from domain.entities.user import UserRole

router = APIRouter(prefix="/api/constructor", tags=["Конструктор шаблонов"])


class BuildTemplateBody(BaseModel):
    step_choices: Dict[str, Any]
    template_name: str
    template_description: str = ""


def _current_user_telegram_id(request_user: Any) -> Optional[int]:
    """Из объекта пользователя (User или dict) получить telegram_id."""
    from fastapi.responses import RedirectResponse
    if isinstance(request_user, RedirectResponse):
        return None
    if hasattr(request_user, "telegram_id"):
        return getattr(request_user, "telegram_id", None)
    if isinstance(request_user, dict):
        return request_user.get("telegram_id") or request_user.get("id")
    return None


@router.get("/contract-types")
async def list_contract_types(
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Список типов договоров."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    types_list = await svc.get_contract_types(session)
    return JSONResponse({"success": True, "contract_types": types_list})


@router.get("/flows")
async def list_flows(
    contract_type_id: Optional[int] = None,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Список активных flows, опционально по типу договора."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    flows_list = await svc.get_flows(session, contract_type_id=contract_type_id)
    return JSONResponse({"success": True, "flows": flows_list})


@router.get("/flows/{flow_id}")
async def get_flow_with_steps(
    flow_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Flow с шагами для мастера."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    flow = await svc.get_flow_with_steps(session, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow не найден")
    return JSONResponse({"success": True, "flow": flow})


@router.post("/flows/{flow_id}/build-template")
async def build_template(
    flow_id: int,
    body: BuildTemplateBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Собрать шаблон из step_choices и создать ContractTemplate."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    telegram_id = _current_user_telegram_id(current_user)
    if telegram_id is None:
        raise HTTPException(status_code=401, detail="Не удалось определить пользователя")
    svc = ConstructorService()
    try:
        template = await svc.build_template(
            session=session,
            flow_id=flow_id,
            step_choices=body.step_choices,
            template_name=body.template_name,
            template_description=body.template_description,
            created_by_telegram_id=telegram_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("build_template error")
        raise HTTPException(status_code=500, detail=str(e))
    if not template:
        raise HTTPException(status_code=400, detail="Не удалось создать шаблон")
    return JSONResponse({"success": True, "template_id": template.id})
