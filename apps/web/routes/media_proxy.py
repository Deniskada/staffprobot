"""Прокси-роут для доступа к медиа файлам из хранилища (restruct1 Фаза 1.4)."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from core.logging.logger import logger
from shared.services.media_storage import get_media_storage_client
from core.config.settings import settings
from urllib.parse import unquote

router = APIRouter()


@router.get("/api/media/{key:path}")
async def proxy_media(
    request: Request,
    key: str,
):
    """
    Проксирует запросы к медиа файлам из хранилища.
    
    Args:
        key: Путь к файлу в хранилище (например, cancellations/1610/file.jpg)
    
    Returns:
        Response с содержимым файла
    """
    try:
        # Декодируем URL-кодированный ключ
        key = unquote(key)
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
