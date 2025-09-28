"""
API endpoints для загрузки медиа-файлов в системе отзывов.
"""

from fastapi import APIRouter, Request, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from shared.services.media_service import MediaService
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.logging.logger import logger
from typing import List, Optional

router = APIRouter()


@router.post("/upload")
async def upload_media_files(
    request: Request,
    files: List[UploadFile] = File(...),
    review_id: int = Form(...),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Загрузка медиа-файлов для отзыва.
    
    Args:
        files: Список файлов для загрузки
        review_id: ID отзыва
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат загрузки
    """
    try:
        # Проверяем права доступа к отзыву
        # TODO: Добавить проверку прав на отзыв
        
        if not files:
            raise HTTPException(status_code=400, detail="Не выбраны файлы для загрузки")
        
        # Инициализируем сервис медиа
        media_service = MediaService()
        
        # Загружаем файлы
        uploaded_media = await media_service.upload_files(db, files, review_id)
        
        if not uploaded_media:
            raise HTTPException(status_code=400, detail="Не удалось загрузить файлы")
        
        # Формируем ответ
        media_info = []
        for media in uploaded_media:
            media_info.append({
                "id": media.id,
                "file_type": media.file_type,
                "file_size": media.file_size,
                "mime_type": media.mime_type,
                "is_primary": media.is_primary,
                "url": media_service.get_file_url(media),
                "created_at": media.created_at.isoformat()
            })
        
        logger.info(f"Uploaded {len(uploaded_media)} media files for review {review_id}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Загружено {len(uploaded_media)} файлов",
            "media": media_info
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading media files: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файлов: {str(e)}")


@router.delete("/{media_id}")
async def delete_media_file(
    request: Request,
    media_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Удаление медиа-файла.
    
    Args:
        media_id: ID медиа-файла
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат удаления
    """
    try:
        # Проверяем права доступа к медиа-файлу
        # TODO: Добавить проверку прав на медиа-файл
        
        # Инициализируем сервис медиа
        media_service = MediaService()
        
        # Удаляем файл
        success = await media_service.delete_file(db, media_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Медиа-файл не найден")
        
        logger.info(f"Deleted media file: {media_id}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Файл успешно удален"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting media file: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")


@router.get("/review/{review_id}")
async def get_review_media(
    request: Request,
    review_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение всех медиа-файлов отзыва.
    
    Args:
        review_id: ID отзыва
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список медиа-файлов
    """
    try:
        # Проверяем права доступа к отзыву
        # TODO: Добавить проверку прав на отзыв
        
        # Инициализируем сервис медиа
        media_service = MediaService()
        
        # Получаем медиа-файлы
        media_files = await media_service.get_media_by_review(db, review_id)
        
        # Формируем ответ
        media_info = []
        for media in media_files:
            media_info.append({
                "id": media.id,
                "file_type": media.file_type,
                "file_size": media.file_size,
                "mime_type": media.mime_type,
                "is_primary": media.is_primary,
                "url": media_service.get_file_url(media),
                "created_at": media.created_at.isoformat()
            })
        
        return JSONResponse(content={
            "success": True,
            "media": media_info
        })
        
    except Exception as e:
        logger.error(f"Error getting review media: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения медиа-файлов: {str(e)}")


@router.post("/validate")
async def validate_files(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(require_employee_or_applicant)
):
    """
    Валидация файлов перед загрузкой.
    
    Args:
        files: Список файлов для валидации
        current_user: Текущий пользователь
        
    Returns:
        JSONResponse: Результат валидации
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="Не выбраны файлы для валидации")
        
        # Инициализируем сервис медиа
        media_service = MediaService()
        
        validation_results = []
        
        for file in files:
            try:
                # Определяем тип файла
                file_type = media_service._get_file_type_from_mime(file.content_type)
                
                if not file_type:
                    validation_results.append({
                        "filename": file.filename,
                        "valid": False,
                        "error": f"Неподдерживаемый формат файла: {file.content_type}"
                    })
                    continue
                
                # Валидируем файл
                await media_service.validate_file(file, file_type)
                
                validation_results.append({
                    "filename": file.filename,
                    "valid": True,
                    "file_type": file_type,
                    "mime_type": file.content_type
                })
                
            except HTTPException as e:
                validation_results.append({
                    "filename": file.filename,
                    "valid": False,
                    "error": e.detail
                })
        
        valid_files = [r for r in validation_results if r["valid"]]
        invalid_files = [r for r in validation_results if not r["valid"]]
        
        return JSONResponse(content={
            "success": True,
            "total_files": len(files),
            "valid_files": len(valid_files),
            "invalid_files": len(invalid_files),
            "results": validation_results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating files: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка валидации файлов: {str(e)}")


@router.get("/limits")
async def get_upload_limits():
    """
    Получение ограничений загрузки файлов.
    
    Returns:
        JSONResponse: Информация об ограничениях
    """
    media_service = MediaService()
    
    limits = {}
    for file_type, max_size in media_service.MAX_SIZES.items():
        limits[file_type] = {
            "max_size_bytes": max_size,
            "max_size_mb": round(max_size / (1024 * 1024), 1),
            "allowed_mime_types": media_service.ALLOWED_MIME_TYPES[file_type]
        }
    
    return JSONResponse(content={
        "success": True,
        "limits": limits
    })
