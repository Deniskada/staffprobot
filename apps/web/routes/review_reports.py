"""
API endpoints для отчетов по отзывам и рейтингам.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from core.database.session import get_db_session
from apps.web.middleware.role_middleware import require_owner_or_superadmin, require_manager_or_superadmin
from core.logging.logger import logger
from typing import Optional, List
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/reviews-summary")
async def get_reviews_summary(
    request: Request,
    period_days: int = Query(default=30, ge=1, le=365, description="Период в днях"),
    target_type: Optional[str] = Query(default=None, description="Тип цели: 'employee' или 'object'"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение сводного отчета по отзывам.
    
    Args:
        period_days: Период в днях
        target_type: Фильтр по типу цели
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Сводный отчет по отзывам
    """
    try:
        from sqlalchemy import select, func, and_
        from domain.entities.review import Review
        from domain.entities.rating import Rating
        
        # Определяем дату начала периода
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Базовый запрос для отзывов (исключаем отклоненные)
        base_query = select(Review).where(
            and_(
                Review.created_at >= start_date,
                Review.status != 'rejected'
            )
        )
        
        if target_type:
            base_query = base_query.where(Review.target_type == target_type)
        
        # Общая статистика отзывов
        total_reviews_query = select(func.count(Review.id)).select_from(base_query.subquery())
        total_result = await db.execute(total_reviews_query)
        total_reviews = total_result.scalar()
        
        # Статистика по статусам
        status_stats_query = select(
            Review.status,
            func.count(Review.id).label('count')
        ).select_from(base_query.subquery()).group_by(Review.status)
        
        status_result = await db.execute(status_stats_query)
        status_stats = {row.status: row.count for row in status_result}
        
        # Статистика по типам целей
        type_stats_query = select(
            Review.target_type,
            func.count(Review.id).label('count')
        ).select_from(base_query.subquery()).group_by(Review.target_type)
        
        type_result = await db.execute(type_stats_query)
        type_stats = {row.target_type: row.count for row in type_result}
        
        # Получаем отзывы для расчета рейтингов (исключаем успешно обжалованные)
        from domain.entities.review import ReviewAppeal
        
        # Сначала получаем все одобренные отзывы
        approved_reviews_query = base_query.where(Review.status == 'approved')
        approved_result = await db.execute(approved_reviews_query)
        all_approved_reviews = approved_result.scalars().all()
        
        # Фильтруем отзывы с успешно обжалованными обжалованиями
        filtered_reviews = []
        for review in all_approved_reviews:
            appeal_query = select(ReviewAppeal).where(
                and_(
                    ReviewAppeal.review_id == review.id,
                    ReviewAppeal.status == 'approved'
                )
            )
            appeal_result = await db.execute(appeal_query)
            appeal = appeal_result.scalar_one_or_none()
            
            # Если обжалования нет или оно не одобрено, включаем отзыв
            if not appeal:
                filtered_reviews.append(review)
        
        # Рассчитываем средние рейтинги
        avg_ratings = {}
        if filtered_reviews:
            type_ratings = {}
            type_counts = {}
            
            for review in filtered_reviews:
                target_type = review.target_type
                rating = float(review.rating)
                
                if target_type not in type_ratings:
                    type_ratings[target_type] = 0.0
                    type_counts[target_type] = 0
                
                type_ratings[target_type] += rating
                type_counts[target_type] += 1
            
            for target_type in type_ratings:
                avg_ratings[target_type] = type_ratings[target_type] / type_counts[target_type]
        
        # Топ отзывов по рейтингу
        top_reviews = []
        if filtered_reviews:
            # Сортируем по рейтингу и берем топ 10
            sorted_reviews = sorted(filtered_reviews, key=lambda r: float(r.rating), reverse=True)[:10]
            
            for review in sorted_reviews:
                top_reviews.append({
                    "id": review.id,
                    "target_type": review.target_type,
                    "target_id": review.target_id,
                    "rating": float(review.rating),
                    "title": review.title,
                    "created_at": review.created_at.isoformat()
                })
        
        return JSONResponse(content={
            "success": True,
            "period_days": period_days,
            "start_date": start_date.isoformat(),
            "summary": {
                "total_reviews": total_reviews,
                "status_breakdown": status_stats,
                "type_breakdown": type_stats,
                "average_ratings": avg_ratings
            },
            "top_reviews": top_reviews
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reviews summary: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения сводного отчета: {str(e)}")


@router.get("/reviews-by-object")
async def get_reviews_by_object(
    request: Request,
    object_id: int = Query(..., description="ID объекта"),
    period_days: int = Query(default=30, ge=1, le=365, description="Период в днях"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение отзывов по конкретному объекту.
    
    Args:
        object_id: ID объекта
        period_days: Период в днях
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Отзывы по объекту
    """
    try:
        from sqlalchemy import select, and_
        from domain.entities.review import Review, ReviewMedia
        from domain.entities.rating import Rating
        
        # Определяем дату начала периода
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Получаем отзывы по объекту
        reviews_query = select(Review).where(
            and_(
                Review.target_type == 'object',
                Review.target_id == object_id,
                Review.created_at >= start_date
            )
        ).order_by(Review.created_at.desc())
        
        result = await db.execute(reviews_query)
        reviews = result.scalars().all()
        
        # Форматируем отзывы
        formatted_reviews = []
        for review in reviews:
            # Получаем медиа-файлы
            media_query = select(ReviewMedia).where(ReviewMedia.review_id == review.id)
            media_result = await db.execute(media_query)
            media_files = media_result.scalars().all()
            
            formatted_reviews.append({
                "id": review.id,
                "rating": float(review.rating),
                "title": review.title,
                "content": review.content,
                "status": review.status,
                "is_anonymous": review.is_anonymous,
                "created_at": review.created_at.isoformat(),
                "published_at": review.published_at.isoformat() if review.published_at else None,
                "media_files": [
                    {
                        "id": media.id,
                        "file_type": media.file_type,
                        "file_size": media.file_size,
                        "mime_type": media.mime_type
                    } for media in media_files
                ]
            })
        
        # Получаем рейтинг объекта
        rating_query = select(Rating).where(
            and_(
                Rating.target_type == 'object',
                Rating.target_id == object_id
            )
        )
        
        rating_result = await db.execute(rating_query)
        rating = rating_result.scalar_one_or_none()
        
        return JSONResponse(content={
            "success": True,
            "object_id": object_id,
            "period_days": period_days,
            "reviews": formatted_reviews,
            "count": len(formatted_reviews),
            "object_rating": {
                "average_rating": float(rating.average_rating) if rating else 5.0,
                "total_reviews": rating.total_reviews if rating else 0,
                "last_updated": rating.last_updated.isoformat() if rating else None
            } if rating else None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reviews by object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов по объекту: {str(e)}")


@router.get("/reviews-by-employee")
async def get_reviews_by_employee(
    request: Request,
    employee_id: int = Query(..., description="ID сотрудника"),
    period_days: int = Query(default=30, ge=1, le=365, description="Период в днях"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение отзывов по конкретному сотруднику.
    
    Args:
        employee_id: ID сотрудника
        period_days: Период в днях
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Отзывы по сотруднику
    """
    try:
        from sqlalchemy import select, and_
        from domain.entities.review import Review, ReviewMedia
        from domain.entities.rating import Rating
        
        # Определяем дату начала периода
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Получаем отзывы по сотруднику
        reviews_query = select(Review).where(
            and_(
                Review.target_type == 'employee',
                Review.target_id == employee_id,
                Review.created_at >= start_date
            )
        ).order_by(Review.created_at.desc())
        
        result = await db.execute(reviews_query)
        reviews = result.scalars().all()
        
        # Форматируем отзывы
        formatted_reviews = []
        for review in reviews:
            # Получаем медиа-файлы
            media_query = select(ReviewMedia).where(ReviewMedia.review_id == review.id)
            media_result = await db.execute(media_query)
            media_files = media_result.scalars().all()
            
            formatted_reviews.append({
                "id": review.id,
                "rating": float(review.rating),
                "title": review.title,
                "content": review.content,
                "status": review.status,
                "is_anonymous": review.is_anonymous,
                "created_at": review.created_at.isoformat(),
                "published_at": review.published_at.isoformat() if review.published_at else None,
                "media_files": [
                    {
                        "id": media.id,
                        "file_type": media.file_type,
                        "file_size": media.file_size,
                        "mime_type": media.mime_type
                    } for media in media_files
                ]
            })
        
        # Получаем рейтинг сотрудника
        rating_query = select(Rating).where(
            and_(
                Rating.target_type == 'employee',
                Rating.target_id == employee_id
            )
        )
        
        rating_result = await db.execute(rating_query)
        rating = rating_result.scalar_one_or_none()
        
        return JSONResponse(content={
            "success": True,
            "employee_id": employee_id,
            "period_days": period_days,
            "reviews": formatted_reviews,
            "count": len(formatted_reviews),
            "employee_rating": {
                "average_rating": float(rating.average_rating) if rating else 5.0,
                "total_reviews": rating.total_reviews if rating else 0,
                "last_updated": rating.last_updated.isoformat() if rating else None
            } if rating else None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reviews by employee: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов по сотруднику: {str(e)}")


@router.get("/moderation-stats")
async def get_moderation_stats(
    request: Request,
    period_days: int = Query(default=30, ge=1, le=365, description="Период в днях"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение статистики модерации.
    
    Args:
        period_days: Период в днях
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Статистика модерации
    """
    try:
        from sqlalchemy import select, func, and_
        from domain.entities.review import Review
        from domain.entities.review_appeal import ReviewAppeal
        
        # Определяем дату начала периода
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Статистика по отзывам
        reviews_query = select(Review).where(Review.created_at >= start_date)
        reviews_result = await db.execute(reviews_query)
        reviews = reviews_result.scalars().all()
        
        # Статистика по обжалованиям
        appeals_query = select(ReviewAppeal).where(ReviewAppeal.created_at >= start_date)
        appeals_result = await db.execute(appeals_query)
        appeals = appeals_result.scalars().all()
        
        # Подсчитываем статистику
        total_reviews = len(reviews)
        pending_reviews = len([r for r in reviews if r.status == 'pending'])
        approved_reviews = len([r for r in reviews if r.status == 'approved'])
        rejected_reviews = len([r for r in reviews if r.status == 'rejected'])
        
        total_appeals = len(appeals)
        pending_appeals = len([a for a in appeals if a.status == 'pending'])
        approved_appeals = len([a for a in appeals if a.status == 'approved'])
        rejected_appeals = len([a for a in appeals if a.status == 'rejected'])
        
        # Время модерации (среднее)
        moderated_reviews = [r for r in reviews if r.status in ['approved', 'rejected'] and r.published_at]
        if moderated_reviews:
            moderation_times = []
            for review in moderated_reviews:
                if review.published_at:
                    time_diff = review.published_at - review.created_at
                    moderation_times.append(time_diff.total_seconds() / 3600)  # в часах
            
            avg_moderation_time = sum(moderation_times) / len(moderation_times)
        else:
            avg_moderation_time = 0
        
        return JSONResponse(content={
            "success": True,
            "period_days": period_days,
            "start_date": start_date.isoformat(),
            "reviews_stats": {
                "total": total_reviews,
                "pending": pending_reviews,
                "approved": approved_reviews,
                "rejected": rejected_reviews,
                "approval_rate": (approved_reviews / total_reviews * 100) if total_reviews > 0 else 0
            },
            "appeals_stats": {
                "total": total_appeals,
                "pending": pending_appeals,
                "approved": approved_appeals,
                "rejected": rejected_appeals,
                "approval_rate": (approved_appeals / total_appeals * 100) if total_appeals > 0 else 0
            },
            "moderation_performance": {
                "average_moderation_time_hours": round(avg_moderation_time, 2),
                "target_moderation_time_hours": 48
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting moderation stats: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики модерации: {str(e)}")
