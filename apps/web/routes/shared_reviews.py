"""
API endpoints для создания и управления отзывами.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database.session import get_db_session
from apps.web.middleware.role_middleware import require_employee_or_applicant, require_owner_or_superadmin, require_any_role
from domain.entities.user import UserRole
from core.logging.logger import logger
from typing import Optional, List
import json

router = APIRouter()


@router.post("/create")
async def create_review(
    request: Request,
    target_type: str = Form(..., description="Тип цели: 'employee' или 'object'"),
    target_id: int = Form(..., description="ID цели"),
    contract_id: int = Form(..., description="ID договора"),
    title: str = Form(..., description="Заголовок отзыва"),
    rating: float = Form(..., description="Оценка от 1.0 до 5.0"),
    content: Optional[str] = Form(None, description="Содержание отзыва"),
    is_anonymous: bool = Form(False, description="Анонимный отзыв"),
    media_files: Optional[List[UploadFile]] = File(None, description="Медиа-файлы"),
    current_user: dict = Depends(require_any_role([UserRole.OWNER, UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.APPLICANT, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Создание отзыва.
    
    Args:
        target_type: Тип цели ('employee' или 'object')
        target_id: ID цели
        contract_id: ID договора
        title: Заголовок отзыва
        rating: Оценка от 1.0 до 5.0
        content: Содержание отзыва
        is_anonymous: Анонимный отзыв
        media_files: Медиа-файлы
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат создания отзыва
    """
    try:
        # Валидация входных данных
        if target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Недопустимый тип цели")
        
        if not (1.0 <= rating <= 5.0):
            raise HTTPException(status_code=400, detail="Оценка должна быть от 1.0 до 5.0")
        
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        if hasattr(current_user, 'telegram_id'):
            user_id = current_user.telegram_id  # Объект User
        elif isinstance(current_user, dict):
            user_id = current_user.get('id')  # Словарь с Telegram ID
        else:
            raise HTTPException(status_code=401, detail="Пользователь не аутентифицирован")
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Проверяем права на создание отзыва
        from shared.services.review_permission_service import ReviewPermissionService
        
        permission_service = ReviewPermissionService(db)
        permission_check = await permission_service.can_create_review(
            user_id=user_obj.id,
            target_type=target_type,
            target_id=target_id,
            contract_id=contract_id
        )
        
        if not permission_check["can_create"]:
            raise HTTPException(status_code=403, detail=permission_check["reason"])
        
        # Создаем отзыв
        from domain.entities.review import Review
        
        review = Review(
            reviewer_id=user_obj.id,
            target_type=target_type,
            target_id=target_id,
            contract_id=contract_id,
            rating=rating,
            title=title,
            content=content,
            is_anonymous=is_anonymous,
            status='pending'
        )
        
        db.add(review)
        await db.commit()
        await db.refresh(review)
        
        # Обрабатываем медиа-файлы
        if media_files:
            await _process_media_files(db, review.id, media_files)
        
        # Отправляем уведомления
        await _send_review_created_notifications(db, review)
        
        logger.info(f"Review {review.id} created by user {user_obj.id}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Отзыв отправлен на модерацию",
            "review": {
                "id": review.id,
                "target_type": review.target_type,
                "target_id": review.target_id,
                "rating": float(review.rating),
                "title": review.title,
                "status": review.status,
                "created_at": review.created_at.isoformat()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания отзыва: {str(e)}")


@router.get("/my-reviews")
async def get_my_reviews(
    request: Request,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(require_any_role([UserRole.OWNER, UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.APPLICANT, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение отзывов пользователя.
    
    Args:
        target_type: Фильтр по типу цели
        limit: Количество записей
        offset: Смещение
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список отзывов пользователя
    """
    try:
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        if hasattr(current_user, 'telegram_id'):
            user_id = current_user.telegram_id  # Объект User
        elif isinstance(current_user, dict):
            user_id = current_user.get('id')  # Словарь с Telegram ID
        else:
            raise HTTPException(status_code=401, detail="Пользователь не аутентифицирован")
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Получаем отзывы пользователя
        from domain.entities.review import Review, ReviewAppeal
        
        # Для управляющих показываем отзывы О НИХ, а не созданные ими
        if user_obj.role == 'manager':
            # Показываем отзывы о самом управляющем
            query = select(Review).where(
                Review.target_type == 'employee',
                Review.target_id == user_obj.id
            )
        else:
            # Для остальных ролей показываем созданные ими отзывы
            query = select(Review).where(Review.reviewer_id == user_obj.id)
        
        # Исключаем отклоненные отзывы
        query = query.where(Review.status != 'rejected')
        
        if target_type:
            query = query.where(Review.target_type == target_type)
        
        if target_id:
            query = query.where(Review.target_id == target_id)
        
        query = query.order_by(Review.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        reviews = result.scalars().all()
        
        # Форматируем отзывы
        formatted_reviews = []
        for review in reviews:
            # Получаем информацию об обжаловании
            appeal_query = select(ReviewAppeal).where(ReviewAppeal.review_id == review.id)
            appeal_result = await db.execute(appeal_query)
            appeal = appeal_result.scalar_one_or_none()
            
            # Пропускаем отзывы с успешно обжалованными обжалованиями
            if appeal and appeal.status == 'approved':
                continue
            
            # Получаем информацию о цели отзыва
            target_info = None
            if review.target_type == 'employee':
                from domain.entities.user import User
                target_query = select(User).where(User.id == review.target_id)
                target_result = await db.execute(target_query)
                target_user = target_result.scalar_one_or_none()
                if target_user:
                    target_info = {
                        "name": f"{target_user.first_name} {target_user.last_name}",
                        "position": "Сотрудник"  # Можно добавить должность в будущем
                    }
            elif review.target_type == 'object':
                from domain.entities.object import Object
                target_query = select(Object).where(Object.id == review.target_id)
                target_result = await db.execute(target_query)
                target_object = target_result.scalar_one_or_none()
                if target_object:
                    target_info = {
                        "name": target_object.name,
                        "position": "Объект"
                    }
            
            formatted_reviews.append({
                "id": review.id,
                "target_type": review.target_type,
                "target_id": review.target_id,
                "target_info": target_info,
                "contract_id": review.contract_id,
                "rating": float(review.rating),
                "title": review.title,
                "content": review.content,
                "status": review.status,
                "is_anonymous": review.is_anonymous,
                "created_at": review.created_at.isoformat(),
                "published_at": review.published_at.isoformat() if review.published_at else None,
                "moderation_notes": review.moderation_notes,
                "appeal_status": appeal.status if appeal else None,
                "appeal_decision": appeal.moderator_decision if appeal else None
            })
        
        return JSONResponse(content={
            "success": True,
            "reviews": formatted_reviews,
            "count": len(formatted_reviews)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов: {str(e)}")


@router.get("/targets/{target_type}")
async def get_available_targets(
    request: Request,
    target_type: str,
    current_user: dict = Depends(require_any_role([UserRole.OWNER, UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.APPLICANT, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение доступных целей для создания отзыва.
    
    Args:
        target_type: Тип цели ('employee' или 'object')
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список доступных целей
    """
    try:
        print(f"DEBUG: get_available_targets called with target_type={target_type}")
        print(f"DEBUG: current_user type: {type(current_user)}")
        print(f"DEBUG: current_user: {current_user}")
        
        if target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Недопустимый тип цели")
        
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        if hasattr(current_user, 'id'):
            # current_user - это объект User
            user_obj = current_user
        elif isinstance(current_user, dict):
            # current_user - это словарь, нужно получить объект User
            telegram_id = current_user.get('id')
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await db.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            
            if not user_obj:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
        else:
            raise HTTPException(status_code=401, detail="Пользователь не аутентифицирован")
        
        # Получаем доступные цели
        from shared.services.review_permission_service import ReviewPermissionService
        
        permission_service = ReviewPermissionService(db)
        available_targets = await permission_service.get_available_targets_for_review(
            user_id=user_obj.id,
            target_type=target_type
        )
        
        return JSONResponse(content={
            "success": True,
            "target_type": target_type,
            "available_targets": available_targets,
            "count": len(available_targets)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available targets: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения доступных целей: {str(e)}")


@router.get("/{review_id}")
async def get_review_details(
    request: Request,
    review_id: int,
    current_user: dict = Depends(require_any_role([UserRole.OWNER, UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.APPLICANT, UserRole.SUPERADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение детальной информации об отзыве.
    
    Args:
        review_id: ID отзыва
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Детальная информация об отзыве
    """
    try:
        from sqlalchemy import select
        from domain.entities.review import Review, ReviewMedia
        
        # Получаем отзыв
        query = select(Review).where(Review.id == review_id)
        result = await db.execute(query)
        review = result.scalar_one_or_none()
        
        if not review:
            raise HTTPException(status_code=404, detail="Отзыв не найден")
        
        # Получаем медиа-файлы
        media_query = select(ReviewMedia).where(ReviewMedia.review_id == review_id)
        media_result = await db.execute(media_query)
        media_files = media_result.scalars().all()
        
        # Форматируем медиа-файлы
        formatted_media = []
        for media in media_files:
            formatted_media.append({
                "id": media.id,
                "file_type": media.file_type,
                "file_size": media.file_size,
                "mime_type": media.mime_type,
                "is_primary": media.is_primary,
                "created_at": media.created_at.isoformat()
            })
        
        return JSONResponse(content={
            "success": True,
            "review": {
                "id": review.id,
                "target_type": review.target_type,
                "target_id": review.target_id,
                "contract_id": review.contract_id,
                "rating": float(review.rating),
                "title": review.title,
                "content": review.content,
                "status": review.status,
                "is_anonymous": review.is_anonymous,
                "reviewer_id": review.reviewer_id,
                "created_at": review.created_at.isoformat(),
                "published_at": review.published_at.isoformat() if review.published_at else None,
                "moderation_notes": review.moderation_notes
            },
            "media_files": formatted_media
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting review details: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения деталей отзыва: {str(e)}")




async def _process_media_files(db: AsyncSession, review_id: int, media_files: List[UploadFile]) -> None:
    """
    Обработка медиа-файлов отзыва.
    
    Args:
        db: Сессия базы данных
        review_id: ID отзыва
        media_files: Список файлов
    """
    try:
        from shared.services.media_service import MediaService
        from domain.entities.review import ReviewMedia
        
        media_service = MediaService(db)
        
        for i, file in enumerate(media_files):
            # Определяем тип файла по MIME-типу
            file_type = _get_file_type(file.content_type)
            
            # Загружаем файл
            uploaded_file = await media_service.upload_file(file, file_type)
            
            # Создаем запись в БД
            review_media = ReviewMedia(
                review_id=review_id,
                file_type=file_type,
                file_path=uploaded_file["file_path"],
                file_size=uploaded_file["file_size"],
                mime_type=uploaded_file["mime_type"],
                is_primary=(i == 0)  # Первый файл - основной
            )
            
            db.add(review_media)
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing media files: {e}")


def _get_file_type(mime_type: str) -> str:
    """
    Определение типа файла по MIME-типу.
    
    Args:
        mime_type: MIME-тип файла
        
    Returns:
        str: Тип файла
    """
    if mime_type.startswith('image/'):
        return 'photo'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    else:
        return 'document'


async def _send_review_created_notifications(db: AsyncSession, review) -> None:
    """
    Отправка уведомлений о создании отзыва.
    
    Args:
        db: Сессия базы данных
        review: Объект отзыва
    """
    try:
        from shared.templates.notifications.review_notifications import ReviewNotificationService
        
        notification_service = ReviewNotificationService(db)
        
        # Отправляем уведомление автору отзыва
        await notification_service.send_review_submitted_notification(
            user_id=review.reviewer_id,
            review_data={
                "target_type": "сотруднику" if review.target_type == "employee" else "объекту",
                "target_id": review.target_id
            }
        )
        
        # Отправляем уведомление модераторам
        await notification_service.send_moderation_required_notification(
            review_id=review.id,
            review_data={
                "target_type": review.target_type,
                "target_id": review.target_id
            }
        )
        
    except Exception as e:
        logger.error(f"Error sending review created notifications: {e}")
