"""API конструктора шаблонов договоров (owner)."""

from typing import Any, Dict, List, Optional

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


@router.get("/contract-types/{type_id}/full-body")
async def get_full_body(
    type_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Получить full_body типа договора."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    data = await svc.get_contract_type_full_body(session, type_id)
    if not data:
        raise HTTPException(status_code=404, detail="Тип договора не найден")
    return JSONResponse({"success": True, **data})


class UpdateFullBodyBody(BaseModel):
    full_body: str


class PreviewFullBodyBody(BaseModel):
    full_body: str


@router.post("/preview-full-body")
async def preview_full_body(
    body: PreviewFullBodyBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
):
    """Превью full_body с заглушками."""
    from fastapi.responses import RedirectResponse
    from jinja2 import Template as JinjaTemplate
    from shared.services.contract_full_body_renderer import get_preview_context
    if isinstance(current_user, RedirectResponse):
        return current_user
    try:
        ctx = get_preview_context()
        html = JinjaTemplate(body.full_body or "").render(ctx)
        return JSONResponse({"success": True, "preview": html})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.put("/contract-types/{type_id}/full-body")
async def update_full_body(
    type_id: int,
    body: UpdateFullBodyBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Обновить full_body типа договора."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    ok = await svc.update_contract_type_full_body(session, type_id, body.full_body)
    if not ok:
        raise HTTPException(status_code=404, detail="Тип договора не найден")
    return JSONResponse({"success": True})


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


@router.get("/flows/editor")
async def list_flows_for_editor(
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Все flows для редактора, сгруппированные по типу."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    data = await svc.get_flows_for_editor(session)
    return JSONResponse({"success": True, **data})


class UpdateFlowBody(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/flows/{flow_id}")
async def get_flow_with_steps(
    flow_id: int,
    for_editor: bool = False,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Flow с шагами для мастера или редактора (for_editor=1 — без фильтра is_active)."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    flow_obj = await svc.get_flow_by_id(session, flow_id, for_editor=for_editor)
    if not flow_obj:
        raise HTTPException(status_code=404, detail="Flow не найден")
    steps = sorted(flow_obj.steps, key=lambda s: s.sort_order)
    flow = {
        "id": flow_obj.id,
        "contract_type_id": flow_obj.contract_type_id,
        "name": flow_obj.name,
        "version": flow_obj.version,
        "is_active": flow_obj.is_active,
        "steps": [
            {
                "id": s.id,
                "sort_order": s.sort_order,
                "title": s.title,
                "slug": s.slug,
                "schema": s.schema or {},
                "request_at_conclusion": s.request_at_conclusion,
            }
            for s in steps
        ],
    }
    return JSONResponse({"success": True, "flow": flow})


@router.put("/flows/{flow_id}")
async def update_flow(
    flow_id: int,
    body: UpdateFlowBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Обновить flow (name, version, is_active)."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    ok = await svc.update_flow(
        session, flow_id,
        name=body.name,
        version=body.version,
        is_active=body.is_active,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Flow не найден")
    return JSONResponse({"success": True})


@router.get("/flows/{flow_id}/steps")
async def list_steps(
    flow_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Список шагов flow для редактора."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    flow = await svc.get_flow_by_id(session, flow_id, for_editor=True)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow не найден")
    steps = sorted(flow.steps, key=lambda s: s.sort_order)
    return JSONResponse({
        "success": True,
        "flow": {"id": flow.id, "name": flow.name, "contract_type_id": flow.contract_type_id},
        "steps": [
            {
                "id": s.id,
                "sort_order": s.sort_order,
                "title": s.title,
                "slug": s.slug,
                "schema": s.schema or {},
                "request_at_conclusion": s.request_at_conclusion,
            }
            for s in steps
        ],
    })


class UpdateStepBody(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    step_schema: Optional[Dict[str, Any]] = None  # alias schema для API
    request_at_conclusion: Optional[bool] = None
    sort_order: Optional[int] = None


@router.put("/steps/{step_id}")
async def update_step(
    step_id: int,
    body: UpdateStepBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Обновить шаг."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    ok = await svc.update_step(
        session, step_id,
        title=body.title,
        slug=body.slug,
        schema=body.step_schema,
        request_at_conclusion=body.request_at_conclusion,
        sort_order=body.sort_order,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Шаг не найден")
    return JSONResponse({"success": True})


class ReorderStepsBody(BaseModel):
    step_ids: List[int]


@router.patch("/flows/{flow_id}/steps/reorder")
async def reorder_steps(
    flow_id: int,
    body: ReorderStepsBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Изменить порядок шагов."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    ok = await svc.reorder_steps(session, flow_id, body.step_ids)
    if not ok:
        raise HTTPException(status_code=400, detail="Ошибка переупорядочивания")
    return JSONResponse({"success": True})


@router.get("/steps/{step_id}/fragments")
async def list_fragments(
    step_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Фрагменты шага для редактора."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    frags = await svc.get_fragments_for_step(session, step_id)
    return JSONResponse({"success": True, "fragments": frags})


@router.get("/fragments/{fragment_id}")
async def get_fragment(
    fragment_id: int,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Фрагмент по id."""
    from fastapi.responses import RedirectResponse
    from sqlalchemy import select
    from domain.entities.constructor_flow import ConstructorFragment
    if isinstance(current_user, RedirectResponse):
        return current_user
    result = await session.execute(
        select(ConstructorFragment).where(ConstructorFragment.id == fragment_id)
    )
    frag = result.scalar_one_or_none()
    if not frag:
        raise HTTPException(status_code=404, detail="Фрагмент не найден")
    return JSONResponse({
        "success": True,
        "fragment": {
            "id": frag.id,
            "step_id": frag.step_id,
            "option_key": frag.option_key,
            "fragment_content": frag.fragment_content,
        },
    })


class UpdateFragmentBody(BaseModel):
    fragment_content: str


@router.put("/fragments/{fragment_id}")
async def update_fragment(
    fragment_id: int,
    body: UpdateFragmentBody,
    current_user=Depends(require_any_role([UserRole.OWNER])),
    session: AsyncSession = Depends(get_db_session),
):
    """Обновить fragment_content."""
    from fastapi.responses import RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    svc = ConstructorService()
    ok = await svc.update_fragment(session, fragment_id, body.fragment_content)
    if not ok:
        raise HTTPException(status_code=404, detail="Фрагмент не найден")
    return JSONResponse({"success": True})


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
