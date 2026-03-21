"""MAX API client: отправка сообщений в platform-api.max.ru."""

from __future__ import annotations

from typing import Any, Optional, Tuple

import httpx

from core.config.settings import settings
from core.logging.logger import logger

from .messenger import MessengerFeatures


def _max_api_public_link(payload: Any) -> Optional[str]:
    """Достать публичную ссылку на сообщение из ответа POST /messages (если API отдаёт)."""
    if not isinstance(payload, dict):
        return None
    link_keys = (
        "link",
        "url",
        "share_url",
        "web_link",
        "permalink",
        "message_link",
        "webUrl",
        "public_url",
    )

    def _from_message_dict(m: dict) -> Optional[str]:
        for k in link_keys:
            v = m.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
        body = m.get("body")
        if isinstance(body, dict):
            for k in link_keys:
                v = body.get(k)
                if isinstance(v, str) and v.startswith("http"):
                    return v
        return None

    msg = payload.get("message")
    if isinstance(msg, dict):
        u = _from_message_dict(msg)
        if u:
            return u
    for k in link_keys:
        v = payload.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    body = payload.get("body")
    if isinstance(body, dict):
        inner = body.get("message")
        if isinstance(inner, dict):
            u = _from_message_dict(inner)
            if u:
                return u
        for k in link_keys:
            v = body.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
    return None


class MaxClient:
    """HTTP-клиент для MAX platform-api."""

    BASE_URL = "https://platform-api.max.ru"

    def __init__(self, token: Optional[str] = None):
        self._token = token or settings.max_bot_token

    def _headers(self) -> dict[str, str]:
        """Заголовки с авторизацией. С окт. 2025 MAX требует Authorization вместо access_token в URL."""
        return {"Authorization": self._token} if self._token else {}

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    @staticmethod
    def _first_http_url_in_json(data: Any) -> Optional[str]:
        """Вытащить первый URL из ответа API (как у GET /videos/{token})."""
        if isinstance(data, str) and data.startswith("http"):
            return data
        if isinstance(data, dict):
            for key in ("url", "downloadUrl", "download_url", "src", "link"):
                v = data.get(key)
                if isinstance(v, str) and v.startswith("http"):
                    return v
            urls = data.get("urls")
            if isinstance(urls, dict):
                for v in urls.values():
                    u = MaxClient._first_http_url_in_json(v)
                    if u:
                        return u
            for v in data.values():
                u = MaxClient._first_http_url_in_json(v)
                if u:
                    return u
        elif isinstance(data, list):
            for item in data:
                u = MaxClient._first_http_url_in_json(item)
                if u:
                    return u
        return None

    async def download_image_by_token(self, token: str) -> Tuple[Optional[bytes], str]:
        """
        Скачать изображение по токену вложения из входящего сообщения.
        GET /photos/{token} (симметрично документированному GET /videos/{token}).
        Fallback: GET /files/{token} (наследие TamTam-совместимых клиентов).
        """
        if not self._token or not token:
            return None, "image/jpeg"
        paths = (f"/photos/{token}", f"/files/{token}")
        async with httpx.AsyncClient() as client:
            for path in paths:
                try:
                    r = await client.get(
                        self._url(path),
                        headers=self._headers(),
                        timeout=30.0,
                    )
                except Exception as e:
                    logger.warning(f"MAX download {path[:20]}... failed: {e}")
                    continue
                if r.status_code != 200:
                    continue
                ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
                if "json" in ct or (
                    r.content and r.content[:1] in (b"{", b"[")
                ):
                    try:
                        payload = r.json()
                    except Exception:
                        continue
                    dl = self._first_http_url_in_json(payload)
                    if not dl:
                        logger.warning("MAX photo API: no url in JSON", extra={"path": path})
                        continue
                    r2 = await client.get(dl, timeout=30.0)
                    if r2.status_code != 200:
                        continue
                    ct2 = r2.headers.get("content-type", "image/jpeg") or "image/jpeg"
                    return r2.content, ct2
                if ct.startswith("image/") or not ct:
                    return r.content, ct or "image/jpeg"
        logger.warning("MAX: could not download image by token", extra={"token_prefix": token[:12]})
        return None, "image/jpeg"

    def _build_attachments(
        self, keyboard: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Логический формат → MAX inline_keyboard attachment."""
        rows: list[list[dict[str, Any]]] = []
        for row in keyboard:
            max_row: list[dict[str, Any]] = []
            for btn in row:
                if btn.get("url"):
                    max_row.append({"type": "link", "text": btn["text"], "url": btn["url"]})
                elif btn.get("callback_data"):
                    max_row.append({
                        "type": "callback",
                        "text": btn["text"],
                        "payload": btn["callback_data"],
                    })
            if max_row:
                rows.append(max_row)
        return [{"type": "inline_keyboard", "payload": {"buttons": rows}}]

    async def send_text(
        self,
        chat_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        parse_mode: Optional[str] = None,
    ) -> None:
        """POST /messages — отправка текста. format=html для разметки (TG-совместимо)."""
        fmt = "html"
        await self._send_message(chat_id=chat_id, text=text, keyboard=keyboard, format=fmt)

    async def send_to_user(
        self,
        user_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        format: Optional[str] = None,
    ) -> None:
        """POST /messages?user_id= — отправка личного сообщения. format: html|markdown."""
        await self._send_message(user_id=user_id, text=text, keyboard=keyboard, format=format)

    async def _send_message(
        self,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None,
        format: Optional[str] = None,
    ) -> None:
        """POST /messages — chat_id для чатов, user_id для личных сообщений."""
        if not self._token:
            logger.warning("MaxClient: MAX_BOT_TOKEN not set, skip send")
            return
        if not settings.max_features_enabled:
            logger.info("MaxClient: MAX_FEATURES_ENABLED=false, skip outbound")
            return
        payload: dict[str, Any] = {"text": text}
        if keyboard:
            payload["attachments"] = self._build_attachments(keyboard)
        if format:
            payload["format"] = format
        if user_id:
            url = self._url("/messages") + f"?user_id={user_id}"
        elif chat_id:
            url = self._url("/messages") + f"?chat_id={chat_id}"
        else:
            raise ValueError("Need chat_id or user_id")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url,
                json=payload,
                headers=self._headers(),
            )
            if r.status_code >= 400:
                logger.error(
                    "MAX API send failed",
                    status=r.status_code,
                    body=r.text[:500],
                    chat_id=chat_id,
                    user_id=user_id,
                )
            r.raise_for_status()
            logger.debug(
                "MAX POST /messages response",
                preview=(r.text[:1200] if r.text else ""),
                chat_id=chat_id,
                user_id=user_id,
            )

    async def _upload_image(self, image_bytes: bytes, content_type: str = "image/jpeg") -> Optional[str]:
        """POST /uploads?type=image → загрузка → возврат token."""
        if not self._token or not settings.max_features_enabled:
            return None
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self._url("/uploads") + "?type=image",
                headers=self._headers(),
            )
            if r.status_code >= 400:
                logger.error("MAX uploads request failed", status=r.status_code, body=r.text[:300])
                return None
            data = r.json()
            upload_url = data.get("url")
            if not upload_url:
                logger.error("MAX uploads: no url in response", body=data)
                return None
            files = {"data": ("image.jpg", image_bytes, content_type)}
            r2 = await client.post(upload_url, files=files)
            if r2.status_code >= 400:
                logger.error("MAX image upload failed", status=r2.status_code, body=r2.text[:300])
                return None
            result = r2.json() if r2.text else {}
            token = result.get("token")
            if not token:
                logger.error("MAX image upload: no token", body=result)
                return None
            return token

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Отправка фото. photo: URL (http/https) или file_id (fallback → текст). Ссылка на сообщение или None."""
        if not self._token or not settings.max_features_enabled:
            logger.warning("MaxClient: skip send_photo (no token or MAX disabled)")
            return None
        image_token: Optional[str] = None
        if photo.startswith(("http://", "https://")):
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(photo, timeout=15.0)
                    if r.status_code == 200:
                        ct = r.headers.get("content-type", "image/jpeg")
                        if "image/" not in ct:
                            ct = "image/jpeg"
                        image_token = await self._upload_image(r.content, ct)
            except Exception as e:
                logger.warning(f"MAX send_photo: fetch URL failed {photo[:50]}: {e}")
        if image_token:
            return await self._post_image_message(
                chat_id, user_id, image_token, caption, keyboard
            )
        text = f"{photo}\n{caption}" if caption else photo
        if user_id:
            await self.send_to_user(user_id, text, format="html")
        else:
            await self.send_text(chat_id, text, keyboard)
        return None

    async def _post_image_message(
        self,
        chat_id: str,
        user_id: Optional[str],
        image_token: str,
        caption: Optional[str],
        keyboard: Optional[list[list[dict[str, Any]]]],
    ) -> Optional[str]:
        payload: dict[str, Any] = {"text": caption or ""}
        payload["attachments"] = [{"type": "image", "payload": {"token": image_token}}]
        if keyboard:
            payload["attachments"].extend(self._build_attachments(keyboard))
        if payload["text"]:
            payload["format"] = "html"
        dest = f"?user_id={user_id}" if user_id else f"?chat_id={chat_id}"
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self._url("/messages") + dest,
                json=payload,
                headers=self._headers(),
            )
            if r.status_code >= 400:
                logger.error("MAX send_photo failed", status=r.status_code, body=r.text[:300])
            r.raise_for_status()
            logger.debug("MAX POST /messages (image) response", preview=r.text[:1200] if r.text else "")
            try:
                return _max_api_public_link(r.json())
            except Exception:
                return None

    async def send_photo_bytes(
        self,
        chat_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
        caption: Optional[str] = None,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Отправка из памяти без HTTP-скачивания по URL. Возвращает ссылку на сообщение, если API отдал."""
        if not self._token:
            logger.warning("MaxClient: MAX_BOT_TOKEN not set, skip send_photo_bytes")
            return None
        ct = content_type if content_type and "image/" in content_type else "image/jpeg"
        image_token = await self._upload_image(image_bytes, ct)
        if image_token:
            return await self._post_image_message(
                chat_id, user_id, image_token, caption, keyboard
            )
        logger.error("MAX send_photo_bytes: upload token failed")
        return None

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        """POST /answers — подтверждение callback. callback_id в query, notification в body."""
        if not self._token:
            return
        url = self._url("/answers") + f"?callback_id={callback_id}"
        payload = {"notification": text or "ok"}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url,
                json=payload,
                headers=self._headers(),
            )
            r.raise_for_status()


class MaxMessenger:
    """Messenger-реализация для MAX."""

    name = "max"
    features = MessengerFeatures(supports_contact_request=False, supports_webapp=False)

    def __init__(self, client: Optional[MaxClient] = None):
        self._client = client or MaxClient()

    async def send_text(
        self,
        chat_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        parse_mode: Optional[str] = None,
    ) -> None:
        await self._client.send_text(chat_id, text, keyboard, parse_mode)

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
    ) -> Optional[str]:
        return await self._client.send_photo(chat_id, photo, caption, keyboard)

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        await self._client.answer_callback(callback_id, text)
