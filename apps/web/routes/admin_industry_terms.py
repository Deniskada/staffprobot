from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import require_superadmin
from core.database.session import get_db_session
from shared.services.industry_terms_service import IndustryTermsService
from shared.services.yandex_gpt_service import generate_industry_term_variants

router = APIRouter()


@router.get("/admin/industry-terms", response_class=HTMLResponse)
async def industry_terms_page(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    terms = await IndustryTermsService.list_terms(db)
    return templates.TemplateResponse(
        "admin/industry_terms.html",
        {"request": request, "current_user": current_user, "terms": terms},
    )


@router.get("/admin/api/industry-terms")
async def list_terms(
    industry: str | None = None,
    language: str = "ru",
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    rows = await IndustryTermsService.list_terms(db, industry=industry, language=language)
    return {
        "items": [
            {
                "id": x.id,
                "industry": x.industry,
                "language": x.language,
                "term_key": x.term_key,
                "term_value": x.term_value,
                "source": x.source,
                "is_active": x.is_active,
            }
            for x in rows
        ]
    }


@router.post("/admin/api/industry-terms")
async def upsert_term(
    payload: dict,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session),
):
    item = await IndustryTermsService.upsert_term(
        db,
        industry=payload.get("industry", "grocery"),
        language=payload.get("language", "ru"),
        term_key=payload.get("term_key", ""),
        term_value=payload.get("term_value", ""),
        source=payload.get("source", "manual"),
        is_active=bool(payload.get("is_active", True)),
    )
    return {"success": True, "id": item.id}


@router.post("/admin/api/industry-terms/ai-generate")
async def ai_generate(
    payload: dict,
    current_user: dict = Depends(require_superadmin),
):
    industry = payload.get("industry", "grocery")
    language = payload.get("language", "ru")
    keys = payload.get("keys", ["object_singular", "object_plural"])
    text = await generate_industry_term_variants(industry, keys, language=language)
    return {"success": bool(text), "result": text or ""}
