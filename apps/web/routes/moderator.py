"""
API endpoints для интерфейса модератора.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from shared.services.moderation_service import ModerationService
from apps.web.middleware.role_middleware import require_moderator_or_superadmin
from core.logging.logger import logger
from typing import Optional, List

router = APIRouter()


@router.get("/")
async def moderator_dashboard(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Главная страница модератора с общей статистикой.
    
    Args:
        current_user: Текущий пользователь (модератор)
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Статистика модерации
    """
    try:
        moderation_service = ModerationService(db)
        
        # Получаем статистику
        statistics = await moderation_service.get_moderation_statistics()
        
        # Получаем просроченные отзывы
        overdue_reviews = await moderation_service.get_overdue_reviews()
        
        # Получаем последние отзывы на модерации
        pending_reviews = await moderation_service.get_pending_reviews(limit=5)
        
        # Получаем статистику обжалований
        from shared.services.appeal_service import AppealService
        appeal_service = AppealService(db)
        appeal_statistics = await appeal_service.get_appeal_statistics()
        
        # Получаем просроченные обжалования
        overdue_appeals = await appeal_service.get_overdue_appeals()
        
        # Получаем последние обжалования
        pending_appeals = await appeal_service.get_pending_appeals(limit=5)
        
        return JSONResponse(content={
            "success": True,
            "statistics": statistics,
            "overdue_count": len(overdue_reviews),
            "recent_pending": [
                {
                    "id": review.id,
                    "title": review.title,
                    "rating": float(review.rating),
                    "target_type": review.target_type,
                    "target_id": review.target_id,
                    "created_at": review.created_at.isoformat(),
                    "reviewer_id": review.reviewer_id,
                    "is_anonymous": review.is_anonymous
                }
                for review in pending_reviews
            ],
            "appeal_statistics": appeal_statistics,
            "overdue_appeals_count": len(overdue_appeals),
            "recent_appeals": [
                {
                    "id": appeal.id,
                    "review_id": appeal.review_id,
                    "appeal_reason": appeal.appeal_reason,
                    "appellant_id": appeal.appellant_id,
                    "status": appeal.status,
                    "created_at": appeal.created_at.isoformat()
                }
                for appeal in pending_appeals
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting moderator dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения данных: {str(e)}")


@router.get("/reviews")
async def get_reviews_for_moderation(
    request: Request,
    status: str = Query(default="pending", description="Статус отзывов"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение отзывов для модерации.
    
    Args:
        status: Статус отзывов ('pending', 'overdue')
        limit: Количество записей
        offset: Смещение
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список отзывов
    """
    try:
        moderation_service = ModerationService(db)
        
        if status == "pending":
            reviews = await moderation_service.get_pending_reviews(limit, offset)
        elif status == "overdue":
            overdue_reviews = await moderation_service.get_overdue_reviews()
            reviews = overdue_reviews[offset:offset + limit]
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый статус")
        
        # Форматируем отзывы для ответа
        formatted_reviews = []
        for review in reviews:
            # Получаем информацию о рецензенте (если не анонимный)
            reviewer_info = None
            if not review.is_anonymous:
                # TODO: Получить информацию о пользователе
                reviewer_info = {"id": review.reviewer_id}
            
            # Получаем информацию о цели отзыва
            target_info = {
                "type": review.target_type,
                "id": review.target_id
                # TODO: Получить детальную информацию о цели
            }
            
            formatted_reviews.append({
                "id": review.id,
                "title": review.title,
                "content": review.content,
                "rating": float(review.rating),
                "target_type": review.target_type,
                "target_id": review.target_id,
                "target_info": target_info,
                "contract_id": review.contract_id,
                "is_anonymous": review.is_anonymous,
                "reviewer_info": reviewer_info,
                "status": review.status,
                "moderation_notes": review.moderation_notes,
                "created_at": review.created_at.isoformat(),
                "published_at": review.published_at.isoformat() if review.published_at else None,
                "media_count": len(review.media_files) if hasattr(review, 'media_files') else 0,
                "appeals_count": len(review.appeals) if hasattr(review, 'appeals') else 0
            })
        
        return JSONResponse(content={
            "success": True,
            "reviews": formatted_reviews,
            "count": len(formatted_reviews),
            "status": status,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(formatted_reviews) == limit
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reviews for moderation: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов: {str(e)}")


@router.get("/reviews/{review_id}")
async def get_review_details(
    request: Request,
    review_id: int,
    current_user: dict = Depends(require_moderator_or_superadmin),
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
        from domain.entities.review import Review, ReviewMedia, ReviewAppeal
        
        # Получаем отзыв с связанными данными
        query = select(Review).where(Review.id == review_id)
        result = await db.execute(query)
        review = result.scalar_one_or_none()
        
        if not review:
            raise HTTPException(status_code=404, detail="Отзыв не найден")
        
        # Получаем медиа-файлы
        media_query = select(ReviewMedia).where(ReviewMedia.review_id == review_id)
        media_result = await db.execute(media_query)
        media_files = media_result.scalars().all()
        
        # Получаем обжалования
        appeals_query = select(ReviewAppeal).where(ReviewAppeal.review_id == review_id)
        appeals_result = await db.execute(appeals_query)
        appeals = appeals_result.scalars().all()
        
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
        
        # Форматируем обжалования
        formatted_appeals = []
        for appeal in appeals:
            formatted_appeals.append({
                "id": appeal.id,
                "appeal_reason": appeal.appeal_reason,
                "appeal_evidence": appeal.appeal_evidence,
                "status": appeal.status,
                "moderator_decision": appeal.moderator_decision,
                "decision_notes": appeal.decision_notes,
                "created_at": appeal.created_at.isoformat(),
                "decided_at": appeal.decided_at.isoformat() if appeal.decided_at else None
            })
        
        # Проводим автоматическую модерацию
        moderation_service = ModerationService(db)
        auto_moderation = await moderation_service.auto_moderate_review(review)
        
        return JSONResponse(content={
            "success": True,
            "review": {
                "id": review.id,
                "title": review.title,
                "content": review.content,
                "rating": float(review.rating),
                "target_type": review.target_type,
                "target_id": review.target_id,
                "contract_id": review.contract_id,
                "is_anonymous": review.is_anonymous,
                "reviewer_id": review.reviewer_id,
                "status": review.status,
                "moderation_notes": review.moderation_notes,
                "created_at": review.created_at.isoformat(),
                "published_at": review.published_at.isoformat() if review.published_at else None
            },
            "media_files": formatted_media,
            "appeals": formatted_appeals,
            "auto_moderation": auto_moderation
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting review details: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения деталей отзыва: {str(e)}")


@router.post("/reviews/{review_id}/moderate")
async def moderate_review(
    request: Request,
    review_id: int,
    decision: str = Form(..., description="Решение: 'approved' или 'rejected'"),
    notes: Optional[str] = Form(None, description="Заметки модератора"),
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Модерация отзыва.
    
    Args:
        review_id: ID отзыва
        decision: Решение ('approved' или 'rejected')
        notes: Заметки модератора
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат модерации
    """
    try:
        if decision not in ['approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Недопустимое решение")
        
        moderation_service = ModerationService(db)
        moderator_id = current_user.get('id')  # Telegram ID
        
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_query = select(User).where(User.telegram_id == moderator_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Модератор не найден")
        
        # Проводим модерацию
        success = await moderation_service.moderate_review(
            review_id, user_obj.id, decision, notes
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка при модерации отзыва")
        
        logger.info(f"Review {review_id} moderated by {user_obj.id} with decision {decision}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Отзыв {'одобрен' if decision == 'approved' else 'отклонен'}",
            "review_id": review_id,
            "decision": decision,
            "moderator_id": user_obj.id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moderating review: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка модерации: {str(e)}")


@router.post("/reviews/bulk-moderate")
async def bulk_moderate_reviews(
    request: Request,
    review_ids: List[int] = Form(..., description="Список ID отзывов"),
    decision: str = Form(..., description="Решение: 'approved' или 'rejected'"),
    notes: Optional[str] = Form(None, description="Заметки модератора"),
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Массовая модерация отзывов.
    
    Args:
        review_ids: Список ID отзывов
        decision: Решение
        notes: Заметки модератора
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат массовой модерации
    """
    try:
        if decision not in ['approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Недопустимое решение")
        
        if not review_ids or len(review_ids) > 50:
            raise HTTPException(status_code=400, detail="Количество отзывов должно быть от 1 до 50")
        
        moderation_service = ModerationService(db)
        moderator_id = current_user.get('id')  # Telegram ID
        
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_query = select(User).where(User.telegram_id == moderator_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Модератор не найден")
        
        # Проводим массовую модерацию
        result = await moderation_service.bulk_moderate_reviews(
            review_ids, user_obj.id, decision, notes
        )
        
        logger.info(f"Bulk moderation by {user_obj.id}: {result}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Обработано {result['successful']} из {result['total']} отзывов",
            "result": result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk moderation: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка массовой модерации: {str(e)}")


@router.get("/statistics")
async def get_moderation_statistics(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение статистики модерации.
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Статистика модерации
    """
    try:
        moderation_service = ModerationService(db)
        
        statistics = await moderation_service.get_moderation_statistics()
        
        return JSONResponse(content={
            "success": True,
            "statistics": statistics
        })
        
    except Exception as e:
        logger.error(f"Error getting moderation statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@router.get("/overdue")
async def get_overdue_reviews(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение просроченных отзывов на модерации.
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список просроченных отзывов
    """
    try:
        moderation_service = ModerationService(db)
        
        overdue_reviews = await moderation_service.get_overdue_reviews()
        
        # Форматируем просроченные отзывы
        formatted_reviews = []
        for review in overdue_reviews:
            # Рассчитываем время просрочки
            from datetime import datetime, timedelta
            hours_overdue = (datetime.utcnow() - review.created_at).total_seconds() / 3600 - 48
            
            formatted_reviews.append({
                "id": review.id,
                "title": review.title,
                "rating": float(review.rating),
                "target_type": review.target_type,
                "target_id": review.target_id,
                "created_at": review.created_at.isoformat(),
                "hours_overdue": round(hours_overdue, 1),
                "reviewer_id": review.reviewer_id,
                "is_anonymous": review.is_anonymous
            })
        
        return JSONResponse(content={
            "success": True,
            "overdue_reviews": formatted_reviews,
            "count": len(formatted_reviews)
        })
        
    except Exception as e:
        logger.error(f"Error getting overdue reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения просроченных отзывов: {str(e)}")


@router.post("/reviews/{review_id}/auto-moderate")
async def auto_moderate_review(
    request: Request,
    review_id: int,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Автоматическая модерация отзыва.
    
    Args:
        review_id: ID отзыва
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат автоматической модерации
    """
    try:
        from sqlalchemy import select
        from domain.entities.review import Review
        
        # Получаем отзыв
        query = select(Review).where(Review.id == review_id)
        result = await db.execute(query)
        review = result.scalar_one_or_none()
        
        if not review:
            raise HTTPException(status_code=404, detail="Отзыв не найден")
        
        moderation_service = ModerationService(db)
        
        # Проводим автоматическую модерацию
        auto_result = await moderation_service.auto_moderate_review(review)
        
        return JSONResponse(content={
            "success": True,
            "auto_moderation": auto_result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto moderation: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка автоматической модерации: {str(e)}")


# ==================== ОБЖАЛОВАНИЯ ====================

@router.get("/appeals")
async def get_appeals_for_moderation(
    request: Request,
    status: str = Query(default="pending", description="Статус обжалований"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение обжалований для рассмотрения.
    
    Args:
        status: Статус обжалований ('pending', 'overdue')
        limit: Количество записей
        offset: Смещение
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список обжалований
    """
    try:
        from shared.services.appeal_service import AppealService
        
        appeal_service = AppealService(db)
        
        if status == "pending":
            appeals = await appeal_service.get_pending_appeals(limit, offset)
        elif status == "overdue":
            overdue_appeals = await appeal_service.get_overdue_appeals()
            appeals = overdue_appeals[offset:offset + limit]
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый статус")
        
        # Форматируем обжалования для ответа
        formatted_appeals = []
        for appeal in appeals:
            # Рассчитываем время ожидания
            from datetime import datetime
            days_pending = (datetime.utcnow() - appeal.created_at).days
            
            formatted_appeals.append({
                "id": appeal.id,
                "review_id": appeal.review_id,
                "appellant_id": appeal.appellant_id,
                "appeal_reason": appeal.appeal_reason,
                "appeal_evidence": appeal.appeal_evidence,
                "status": appeal.status,
                "moderator_decision": appeal.moderator_decision,
                "decision_notes": appeal.decision_notes,
                "created_at": appeal.created_at.isoformat(),
                "decided_at": appeal.decided_at.isoformat() if appeal.decided_at else None,
                "days_pending": days_pending
            })
        
        return JSONResponse(content={
            "success": True,
            "appeals": formatted_appeals,
            "count": len(formatted_appeals),
            "status": status,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(formatted_appeals) == limit
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appeals for moderation: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения обжалований: {str(e)}")


@router.get("/appeals/{appeal_id}")
async def get_appeal_details_for_moderation(
    request: Request,
    appeal_id: int,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение детальной информации об обжаловании для модерации.
    
    Args:
        appeal_id: ID обжалования
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Детальная информация об обжаловании
    """
    try:
        from shared.services.appeal_service import AppealService
        
        appeal_service = AppealService(db)
        appeal_details = await appeal_service.get_appeal_details(appeal_id)
        
        if not appeal_details:
            raise HTTPException(status_code=404, detail="Обжалование не найдено")
        
        return JSONResponse(content={
            "success": True,
            "appeal_details": appeal_details
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appeal details: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения деталей обжалования: {str(e)}")


@router.post("/appeals/{appeal_id}/review")
async def review_appeal(
    request: Request,
    appeal_id: int,
    decision: str = Form(..., description="Решение: 'approved' или 'rejected'"),
    decision_notes: Optional[str] = Form(None, description="Заметки модератора"),
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Рассмотрение обжалования модератором.
    
    Args:
        appeal_id: ID обжалования
        decision: Решение ('approved' или 'rejected')
        decision_notes: Заметки модератора
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат рассмотрения
    """
    try:
        if decision not in ['approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Недопустимое решение")
        
        from shared.services.appeal_service import AppealService
        
        appeal_service = AppealService(db)
        moderator_id = current_user.get('id')  # Telegram ID
        
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_query = select(User).where(User.telegram_id == moderator_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Модератор не найден")
        
        # Рассматриваем обжалование
        success = await appeal_service.review_appeal(
            appeal_id=appeal_id,
            moderator_id=user_obj.id,
            decision=decision,
            decision_notes=decision_notes
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка рассмотрения обжалования")
        
        logger.info(f"Appeal {appeal_id} reviewed by {user_obj.id} with decision {decision}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Обжалование {'одобрено' if decision == 'approved' else 'отклонено'}",
            "appeal_id": appeal_id,
            "decision": decision,
            "moderator_id": user_obj.id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing appeal: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка рассмотрения обжалования: {str(e)}")


@router.get("/appeals/overdue")
async def get_overdue_appeals(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение просроченных обжалований.
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список просроченных обжалований
    """
    try:
        from shared.services.appeal_service import AppealService
        
        appeal_service = AppealService(db)
        overdue_appeals = await appeal_service.get_overdue_appeals()
        
        # Форматируем просроченные обжалования
        formatted_appeals = []
        for appeal in overdue_appeals:
            from datetime import datetime
            hours_overdue = (datetime.utcnow() - appeal.created_at).total_seconds() / 3600 - 72
            
            formatted_appeals.append({
                "id": appeal.id,
                "review_id": appeal.review_id,
                "appellant_id": appeal.appellant_id,
                "appeal_reason": appeal.appeal_reason,
                "created_at": appeal.created_at.isoformat(),
                "hours_overdue": round(hours_overdue, 1)
            })
        
        return JSONResponse(content={
            "success": True,
            "overdue_appeals": formatted_appeals,
            "count": len(formatted_appeals)
        })
        
    except Exception as e:
        logger.error(f"Error getting overdue appeals: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения просроченных обжалований: {str(e)}")


@router.get("/appeals/statistics")
async def get_appeal_statistics(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение статистики обжалований.
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Статистика обжалований
    """
    try:
        from shared.services.appeal_service import AppealService
        
        appeal_service = AppealService(db)
        statistics = await appeal_service.get_appeal_statistics()
        
        return JSONResponse(content={
            "success": True,
            "statistics": statistics
        })
        
    except Exception as e:
        logger.error(f"Error getting appeal statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики обжалований: {str(e)}")
