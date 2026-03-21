"""Отправка медиа в Telegram-группу отчётов (для MAX и TG)."""

from __future__ import annotations

from typing import Any, List

import httpx
from core.config.settings import settings
from core.logging.logger import logger


async def send_media_to_telegram_group(
    chat_id: str,
    media_items: List[dict],
    caption: str,
    bot: Any = None,
) -> List[str]:
    """
    Отправить медиа в группу. media_items: [{"url": str, "type": "photo"|"video"} | {"file_id": str, "type": "photo"|"video"}].
    Возвращает список URL сообщений.
    """
    if not media_items:
        return []

    token = getattr(settings, "telegram_bot_token", None)
    if not token and not bot:
        logger.error("No telegram bot token or bot instance")
        return []

    def _build_media(item: dict) -> dict | None:
        t = item.get("type", "photo")
        url = item.get("url")
        fid = item.get("file_id")
        media = url if url else fid
        if not media:
            return None
        return {"type": t, "media": media}

    media_list = []
    for item in media_items:
        m = _build_media(item)
        if m:
            media_list.append(m)

    if not media_list:
        return []

    media_list[0]["caption"] = caption

    try:
        if bot:
            from telegram import InputMediaPhoto, InputMediaVideo

            tg_media = []
            for i, m in enumerate(media_list):
                mt = m["type"]
                media_val = m["media"]
                cap = m.get("caption") if i == 0 else None
                if mt == "photo":
                    tg_media.append(InputMediaPhoto(media=media_val, caption=cap))
                else:
                    tg_media.append(InputMediaVideo(media=media_val, caption=cap))
            sent = await bot.send_media_group(chat_id=chat_id, media=tg_media)
            chat_for_url = str(chat_id).lstrip("-100").lstrip("-")
            return [f"https://t.me/c/{chat_for_url}/{msg.message_id}" for msg in sent]
        if token:
            api_url = f"https://api.telegram.org/bot{token}/sendMediaGroup"
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    api_url,
                    json={"chat_id": chat_id, "media": media_list},
                    timeout=timeout,
                )
                if r.status_code != 200:
                    logger.error(
                        "sendMediaGroup HTTP error",
                        status=r.status_code,
                        body=r.text[:500],
                        chat_id=chat_id,
                    )
                    return []
                data = r.json()
                if not data.get("ok"):
                    logger.error(
                        "sendMediaGroup API ok=false",
                        description=data.get("description"),
                        chat_id=chat_id,
                    )
                    return []
                sent = data.get("result", [])
                chat_for_url = str(chat_id).lstrip("-100").lstrip("-")
                return [f"https://t.me/c/{chat_for_url}/{m.get('message_id', '')}" for m in sent]
    except Exception as e:
        logger.exception(f"Error sending media to group: {e}")
    return []
