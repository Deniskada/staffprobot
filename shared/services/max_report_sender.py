"""Отправка фото-отчётов в группу MAX (platform-api)."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from core.config.settings import settings
from core.logging.logger import logger
from shared.bot_unified.max_client import MaxClient
from shared.services.media_storage import MediaFile, get_media_storage_client
from shared.services.telegram_staging_upload import download_telegram_file


async def send_media_to_max_group(
    chat_id: str,
    media_items: List[dict[str, Any]],
    caption: str,
    uploaded_media: Optional[List[MediaFile]] = None,
) -> Tuple[bool, List[Optional[str]]]:
    """
    По одному сообщению на файл; подпись только у первого.
    Источник: S3 key (get_bytes), Telegram file_id (скачивание), иначе URL.
    Второй элемент — публичные ссылки на сообщения MAX (если API вернул), по одной на файл.
    """
    links: List[Optional[str]] = []
    if not media_items or not str(chat_id).strip():
        return False, links

    client = MaxClient()
    sent_any = False

    p = (settings.media_storage_provider or "minio").strip().lower()
    s3_override = p if p in ("minio", "s3") else "minio"
    storage = get_media_storage_client(bot=None, provider_override=s3_override)
    get_bytes = getattr(storage, "get_bytes", None)

    for i, item in enumerate(media_items):
        cap = caption if i == 0 else None
        max_link: Optional[str] = None
        try:
            if uploaded_media is not None and i < len(uploaded_media):
                mf = uploaded_media[i]
                mu = mf.url or ""
                if mu.startswith("telegram:"):
                    body, ct = await download_telegram_file(mf.key)
                    max_link = await client.send_photo_bytes(
                        str(chat_id),
                        body,
                        content_type=ct or mf.mime_type or "image/jpeg",
                        caption=cap,
                    )
                    sent_any = True
                    links.append(max_link)
                    continue
                if callable(get_bytes):
                    body, ct = await storage.get_bytes(mf.key)
                    max_link = await client.send_photo_bytes(
                        str(chat_id),
                        body,
                        content_type=ct or mf.mime_type or "image/jpeg",
                        caption=cap,
                    )
                    sent_any = True
                    links.append(max_link)
                    continue

            fid = item.get("file_id")
            mtype = item.get("type", "photo")
            if fid and mtype == "photo":
                body, ct = await download_telegram_file(str(fid))
                max_link = await client.send_photo_bytes(
                    str(chat_id),
                    body,
                    content_type=ct or "image/jpeg",
                    caption=cap,
                )
                sent_any = True
                links.append(max_link)
                continue

            url = item.get("url")
            if not url or not str(url).startswith(("http://", "https://")):
                links.append(None)
                continue
            max_link = await client.send_photo(str(chat_id), str(url), caption=cap)
            sent_any = True
            links.append(max_link)
        except Exception as e:
            logger.warning(
                "MAX report group: send failed",
                chat_id=chat_id,
                index=i,
                error=str(e),
            )
            links.append(None)

    return sent_any, links
