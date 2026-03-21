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
    if not settings.max_features_enabled:
        return JSONResponse({"ok": False, "error": "MAX features disabled"}, status_code=503)

    try:
        raw = await request.json()
    except Exception as e:
        logger.warning(f"MAX webhook: invalid JSON: {e}")
        return JSONResponse({"ok": False}, status_code=400)

    from shared.bot_unified import MaxAdapter, MaxMessenger, unified_router

    nu = MaxAdapter.parse(raw)
    if raw.get("update_type") == "message_created":
        body = (raw.get("message") or {}).get("body") or {}
        atts = body.get("attachments") or []
        loc_att = next((a for a in atts if a.get("type") == "location"), None)
        logger.info(
            "MAX message_created",
            extra={
                "att_types": [a.get("type") for a in atts],
                "location_payload": loc_att.get("payload") if loc_att else None,
            },
        )
    if nu:
        messenger = MaxMessenger()
        try:
            if await unified_router.handle(nu, messenger):
                return {"ok": True}
            # Сообщение с геолокацией не обработано — отправить fallback
            has_location = nu.location or (nu.text and "," in (nu.text or ""))
            if not has_location and raw.get("update_type") == "message_created":
                body = (raw.get("message") or {}).get("body") or {}
                has_location = any(
                    a.get("type") in ("location", "geo", "geolocation")
                    for a in (body.get("attachments") or [])
                )
            if nu.messenger == "max" and has_location:
                await _send_location_fallback(nu, messenger)
            return {"ok": True}
        except Exception as e:
            logger.exception(f"MAX webhook handler error: {e}")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return {"ok": True}


async def _send_location_fallback(nu, messenger) -> None:
    """Отправка fallback при необработанной геолокации."""
    try:
        from shared.bot_unified.user_resolver import resolve_for_services
        from core.state import user_state_manager
        from shared.bot_unified.router import START_KEYBOARD

        chat_id = nu.chat_id or (nu.external_user_id and str(nu.external_user_id))
        if not chat_id:
            logger.warning("MAX location fallback: no chat_id", extra={"external_user_id": nu.external_user_id})
            return
        internal_id, _ = await resolve_for_services("max", nu.external_user_id or "")
        state = await user_state_manager.get_state(internal_id) if internal_id else None
        has_parsed_loc = bool(nu.location)
        if not internal_id:
            text = "❌ Аккаунт не привязан. Используйте /start с кодом из ЛК → Мессенджеры."
        elif not has_parsed_loc:
            text = "❌ Не удалось получить координаты. Введите вручную: 55.75,37.61"
        elif not state:
            text = "❌ Сначала выберите действие (Открыть объект / Закрыть объект и т.д.)."
        else:
            text = "❌ Геолокация не ожидается на этом шаге. Выберите действие заново."
        logger.info("MAX location fallback", extra={"chat_id": chat_id, "internal_id": internal_id, "has_state": bool(state)})
        await messenger.send_text(chat_id, text, keyboard=START_KEYBOARD)
    except Exception as e:
        logger.warning(f"MAX location fallback error: {e}")
