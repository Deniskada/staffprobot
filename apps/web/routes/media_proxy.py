"""Прокси-роут для доступа к медиа файлам из хранилища (restruct1 Фаза 1.4)."""

import re
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.logging.logger import logger
from shared.services.media_storage import get_media_storage_client
from core.config.settings import settings
from urllib.parse import unquote
from apps.web.middleware.auth_middleware import get_current_user

router = APIRouter()

_PROFILES_RE = re.compile(r"^profiles/(\d+)/")
_CONTRACTS_RE = re.compile(r"^contracts/(\d+)/")


async def _resolve_user_id(current_user: dict, db_session) -> int | None:
    """Получить внутренний user_id из current_user dict."""
    if not current_user:
        return None
    from domain.entities.user import User
    telegram_id = current_user.get("telegram_id") or current_user.get("id")
    if not telegram_id:
        return None
    result = await db_session.execute(select(User.id).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def _check_media_access(key: str, current_user: dict) -> bool:
    """Проверить права доступа к медиа-файлу по ключу."""
    if not current_user:
        return False

    profiles_match = _PROFILES_RE.match(key)
    contracts_match = _CONTRACTS_RE.match(key)

    if not profiles_match and not contracts_match:
        return True

    from core.database.session import get_async_session
    async with get_async_session() as session:
        user_id = await _resolve_user_id(current_user, session)
        if not user_id:
            return False

        roles = current_user.get("roles", [])
        is_owner = "owner" in roles or "superadmin" in roles
        is_manager = "manager" in roles

        if profiles_match:
            profile_id = int(profiles_match.group(1))
            from domain.entities.profile import Profile
            result = await session.execute(
                select(Profile.user_id).where(Profile.id == profile_id)
            )
            profile_owner_id = result.scalar_one_or_none()
            if not profile_owner_id:
                return False
            if profile_owner_id == user_id:
                return True
            if is_owner or is_manager:
                return True
            return False

        if contracts_match:
            contract_id = int(contracts_match.group(1))
            from domain.entities.contract import Contract
            result = await session.execute(
                select(Contract).where(Contract.id == contract_id)
            )
            contract = result.scalar_one_or_none()
            if not contract:
                return False
            if contract.owner_id == user_id or contract.employee_id == user_id:
                return True
            if is_owner or is_manager:
                return True
            return False

    return False


@router.get("/api/media/{key:path}")
async def proxy_media(
    request: Request,
    key: str,
):
    """
    Проксирует запросы к медиа файлам из хранилища.
    Проверяет авторизацию для profiles/* и contracts/*.
    """
    try:
        # Декодируем URL-кодированный ключ
        key = unquote(key)

        current_user = await get_current_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Не авторизован")

        has_access = await _check_media_access(key, current_user)
        if not has_access:
            raise HTTPException(status_code=403, detail="Нет доступа к файлу")
        # Получаем клиент хранилища
        storage_client = get_media_storage_client()
        
        # Проверяем, что файл существует и получаем его
        # Для S3 используем get_object, для Telegram - другой метод
        if settings.media_storage_provider in ("minio", "s3"):
            # S3-совместимое хранилище
            from shared.services.media_storage.s3_client import S3MediaStorageClient
            from botocore.exceptions import ClientError
            import asyncio
            
            if isinstance(storage_client, S3MediaStorageClient):
                # Получаем объект из S3 через синхронный клиент
                s3_client = storage_client._client
                bucket = storage_client._bucket
                
                try:
                    # Выполняем синхронный вызов в executor
                    def get_object_sync():
                        return s3_client.get_object(Bucket=bucket, Key=key)
                    
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, get_object_sync)
                    
                    # Читаем содержимое
                    content = response["Body"].read()
                    content_type = response.get("ContentType", "application/octet-stream")
                    content_length = response.get("ContentLength", len(content))
                    
                    # Определяем заголовки для ответа
                    headers = {
                        "Content-Type": content_type,
                        "Content-Length": str(content_length),
                        "Cache-Control": "public, max-age=3600",  # Кэшируем на 1 час
                    }
                    
                    # Добавляем заголовок для скачивания, если это не изображение
                    if not content_type.startswith("image/"):
                        headers["Content-Disposition"] = f'attachment; filename="{key.split("/")[-1]}"'
                    
                    return Response(
                        content=content,
                        headers=headers,
                        media_type=content_type,
                    )
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    if error_code == "NoSuchKey":
                        logger.warning("Media file not found", key=key)
                        raise HTTPException(status_code=404, detail="File not found")
                    else:
                        logger.error("Error fetching media from S3", key=key, error=str(e))
                        raise HTTPException(status_code=500, detail="Error fetching file")
            else:
                raise HTTPException(status_code=500, detail="Unsupported storage client type")
        else:
            # Telegram хранилище - возвращаем ошибку, т.к. для Telegram нужен другой подход
            raise HTTPException(
                status_code=501,
                detail="Direct media access not supported for Telegram storage"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error proxying media", key=key, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
