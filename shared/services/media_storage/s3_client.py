"""S3-совместимый клиент медиа-хранилища (MinIO, reg.ru, Cloud.ru, AWS и т.д.)."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from core.config.settings import settings
from core.logging.logger import logger

from .base import MediaFile, MediaStorageClient

BotType = Any

_DEFAULT_MIME: Dict[str, str] = {
    "photo": "image/jpeg",
    "video": "video/mp4",
    "document": "application/octet-stream",
}


def _s3_client(provider: str):
    if provider == "minio":
        return boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",
        )
    if provider == "s3":
        if not all(
            [
                settings.s3_endpoint,
                settings.s3_access_key,
                settings.s3_secret_key,
                settings.s3_bucket,
            ]
        ):
            raise ValueError(
                "S3 storage config incomplete: set S3_ENDPOINT, S3_ACCESS_KEY, "
                "S3_SECRET_KEY, S3_BUCKET (reg.ru, Cloud.ru, AWS и т.д.)"
            )
        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name=settings.s3_region or "us-east-1",
        )
    raise ValueError(f"Unknown S3 provider: {provider}")


def _bucket(provider: str) -> str:
    if provider == "minio":
        return settings.minio_bucket
    return settings.s3_bucket or ""


def _run_sync(fn, *args, **kwargs):
    return asyncio.to_thread(fn, *args, **kwargs)


class S3MediaStorageClient(MediaStorageClient):
    """Хранилище в S3-совместимом бакете (MinIO, reg.ru, Cloud.ru, AWS и т.д.)."""

    def __init__(self, provider: str = "minio") -> None:
        if provider not in ("minio", "s3"):
            raise ValueError(f"provider must be minio|s3, got {provider}")
        self._provider = provider
        self._client = _s3_client(provider)
        self._bucket = _bucket(provider)
        self._expires = settings.media_presigned_expires_seconds

    def _key(self, folder: str, file_name: str) -> str:
        base = os.path.basename(file_name)
        if not base or base == file_name:
            ext = "bin"
            if "." in file_name:
                ext = file_name.rsplit(".", 1)[-1]
            base = f"{uuid.uuid4().hex}.{ext}"
        return f"{folder.rstrip('/')}/{base}"

    async def upload(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MediaFile:
        key = self._key(folder, file_name)
        buf = BytesIO(file_content)
        await _run_sync(
            self._client.upload_fileobj,
            buf,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type or "application/octet-stream"},
        )
        url = await self.get_url(key, self._expires)
        now = datetime.now(timezone.utc)
        m = MediaFile(
            key=key,
            url=url,
            type="document",
            size=len(file_content),
            mime_type=content_type or "application/octet-stream",
            uploaded_at=now,
            metadata=dict(metadata or {}, folder=folder),
        )
        logger.debug("S3 upload", key=key, size=len(file_content), bucket=self._bucket)
        return m

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Получить URL для доступа к файлу.
        
        Для S3-хранилищ возвращает URL веб-приложения (прокси),
        чтобы избежать проблем с внутренними адресами Docker.
        """
        # Используем settings.environment для определения окружения
        # На dev всегда используем settings.domain, на prod - через URLHelper (из БД)
        if settings.environment == "development":
            # На dev используем настройки из .env напрямую
            protocol = "https" if settings.use_https else "http"
            base_url = f"{protocol}://{settings.domain}"
        else:
            # На prod используем URLHelper (берет домен из БД)
            from core.utils.url_helper import URLHelper
            try:
                base_url = await URLHelper.get_web_url()
            except Exception as e:
                # Fallback на настройки из settings, если URLHelper не инициализирован
                logger.warning("URLHelper not initialized, using settings.domain", error=str(e))
                protocol = "https" if settings.use_https else "http"
                base_url = f"{protocol}://{settings.domain}"
        
        # URL-кодируем ключ для безопасной передачи в пути
        import urllib.parse
        encoded_key = urllib.parse.quote(key, safe="")
        return f"{base_url}/api/media/{encoded_key}"

    async def delete(self, key: str) -> bool:
        try:
            await _run_sync(
                self._client.delete_object, Bucket=self._bucket, Key=key
            )
            return True
        except ClientError as e:
            logger.warning("S3 delete failed", key=key, error=str(e))
            return False

    async def list_files(
        self, folder: str, prefix: Optional[str] = None
    ) -> List[MediaFile]:
        p = folder.rstrip("/") + "/"
        if prefix:
            p = p + prefix.lstrip("/")
        out: List[MediaFile] = []
        try:
            pag = await _run_sync(
                self._client.get_paginator("list_objects_v2").paginate,
                Bucket=self._bucket,
                Prefix=p,
            )
            for page in pag:
                for obj in page.get("Contents") or []:
                    k = obj.get("Key")
                    if not k:
                        continue
                    size = obj.get("Size") or 0
                    url = await self.get_url(k, self._expires)
                    out.append(
                        MediaFile(
                            key=k,
                            url=url,
                            type="document",
                            size=size,
                            mime_type="application/octet-stream",
                            uploaded_at=datetime.now(timezone.utc),
                            metadata={},
                        )
                    )
        except ClientError as e:
            logger.warning("S3 list_files failed", prefix=p, error=str(e))
        return out

    async def exists(self, key: str) -> bool:
        try:
            await _run_sync(
                self._client.head_object, Bucket=self._bucket, Key=key
            )
            return True
        except ClientError:
            return False

    async def store_telegram_file(
        self,
        file_id: str,
        folder: str,
        file_type: str,
        bot: BotType,
    ) -> MediaFile:
        if not bot:
            raise ValueError("bot required for S3MediaStorageClient.store_telegram_file")
        tg_file = await bot.get_file(file_id)
        buf = BytesIO()
        await tg_file.download_to_memory(out=buf)
        buf.seek(0)
        content = buf.read()
        ext = "jpg" if file_type == "photo" else "mp4" if file_type == "video" else "bin"
        name = f"{uuid.uuid4().hex}.{ext}"
        mime = _DEFAULT_MIME.get(file_type, "application/octet-stream")
        m = await self.upload(
            content, name, mime, folder, metadata={"telegram_file_id": file_id}
        )
        m.type = file_type
        return m
