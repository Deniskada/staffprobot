"""Временная выгрузка байтов в Telegram для получения file_id (без постоянного сообщения в чате)."""

from __future__ import annotations

import os
from typing import Tuple

import httpx

from core.config.settings import settings
from core.logging.logger import logger


async def stage_photo_as_file_id(
    chat_id: str,
    content: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> str:
    """
    sendPhoto в chat_id → взять file_id → deleteMessage.
    Нужен бот с правом писать в этот чат.
    """
    token = getattr(settings, "telegram_bot_token", None) or ""
    if not token:
        raise ValueError("telegram_bot_token не задан")
    ct = content_type if content_type and "/" in content_type else "image/jpeg"
    api = f"https://api.telegram.org/bot{token}/sendPhoto"
    timeout = httpx.Timeout(25.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            api,
            data={"chat_id": chat_id},
            files={"photo": (filename or "photo.jpg", content, ct)},
        )
        data = r.json() if r.text else {}
        if not data.get("ok"):
            logger.error(
                "Telegram stage sendPhoto failed",
                chat_id=chat_id,
                status=r.status_code,
                description=data.get("description"),
            )
            raise RuntimeError(data.get("description") or r.text or "sendPhoto failed")
        result = data.get("result") or {}
        photos = result.get("photo") or []
        if not photos:
            raise RuntimeError("sendPhoto: нет photo в ответе")
        file_id = photos[-1]["file_id"]
        mid = result.get("message_id")
        if mid is not None:
            del_api = f"https://api.telegram.org/bot{token}/deleteMessage"
            dr = await client.post(
                del_api,
                json={"chat_id": chat_id, "message_id": mid},
            )
            if dr.status_code != 200 or not (dr.json() if dr.text else {}).get("ok"):
                logger.warning(
                    "Telegram stage deleteMessage failed (file_id уже получен)",
                    chat_id=chat_id,
                    message_id=mid,
                    body=(dr.text or "")[:200],
                )
        return str(file_id)


async def download_telegram_file(file_id: str) -> Tuple[bytes, str]:
    """Скачать файл по file_id (для отправки в MAX и т.д.)."""
    token = getattr(settings, "telegram_bot_token", None) or ""
    if not token:
        raise ValueError("telegram_bot_token не задан")
    timeout = httpx.Timeout(40.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        gr = await client.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
        )
        gdata = gr.json() if gr.text else {}
        if not gdata.get("ok"):
            raise RuntimeError(gdata.get("description") or "getFile failed")
        path = (gdata.get("result") or {}).get("file_path") or ""
        if not path:
            raise RuntimeError("getFile: нет file_path")
        ext = (os.path.splitext(path)[1] or "").lower()
        ct = "image/jpeg"
        if ext in (".png",):
            ct = "image/png"
        elif ext in (".webp",):
            ct = "image/webp"
        elif ext in (".gif",):
            ct = "image/gif"
        fu = f"https://api.telegram.org/file/bot{token}/{path}"
        fr = await client.get(fu)
        fr.raise_for_status()
        return fr.content, fr.headers.get("content-type") or ct
