"""MAX Bot webhook endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.config.settings import settings
from core.logging.logger import logger

router = APIRouter()


@router.post(settings.max_webhook_path, include_in_schema=False)
async def max_webhook(request: Request):
    """Приём webhook от platform-api.max.ru."""
    if not settings.max_bot_token:
        return JSONResponse({"ok": False, "error": "MAX bot not configured"}, status_code=503)

    try:
        raw = await request.json()
    except Exception as e:
        logger.warning(f"MAX webhook: invalid JSON: {e}")
        return JSONResponse({"ok": False}, status_code=400)

    from shared.bot_unified import MaxAdapter, MaxMessenger, unified_router

    nu = MaxAdapter.parse(raw)
    if nu:
        messenger = MaxMessenger()
        try:
            if await unified_router.handle(nu, messenger):
                return {"ok": True}
            # Не обработано — пока просто ок
            return {"ok": True}
        except Exception as e:
            logger.error(f"MAX webhook handler error: {e}", exc_info=True)
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return {"ok": True}
