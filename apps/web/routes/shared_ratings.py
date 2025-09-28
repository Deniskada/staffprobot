"""
API endpoints для работы с рейтингами в системе отзывов.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from shared.services.rating_service import RatingService
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.logging.logger import logger
from typing import Optional, List

router = APIRouter()


@router.get("/top/{target_type}")
async def get_top_rated(
    request: Request,
    target_type: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение топ рейтинговых объектов или сотрудников.
    
    Args:
        target_type: Тип цели
        limit: Количество записей
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список топ рейтингов
    """
    try:
        if target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Неподдерживаемый тип цели")
        
        rating_service = RatingService(db)
        
        # Получаем топ рейтинги
        top_ratings = await rating_service.get_top_rated(target_type, limit)
        
        # Форматируем результат
        formatted_ratings = []
        for rating in top_ratings:
            star_info = rating_service.get_star_rating(float(rating.average_rating))
            formatted_ratings.append({
                "id": rating.id,
                "target_type": rating.target_type,
                "target_id": rating.target_id,
                "average_rating": float(rating.average_rating),
                "total_reviews": rating.total_reviews,
                "last_updated": rating.last_updated.isoformat(),
                "stars": star_info
            })
        
        return JSONResponse(content={
            "success": True,
            "top_ratings": formatted_ratings,
            "count": len(formatted_ratings)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top ratings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения топ рейтингов: {str(e)}")


@router.get("/{target_type}/{target_id}")
async def get_rating(
    request: Request,
    target_type: str,
    target_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение рейтинга объекта или сотрудника.
    
    Args:
        target_type: Тип цели ('employee' или 'object')
        target_id: ID цели
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Информация о рейтинге
    """
    try:
        # Валидация типа цели
        if target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Неподдерживаемый тип цели")
        
        rating_service = RatingService(db)
        
        # Получаем рейтинг
        rating = await rating_service.get_rating(target_type, target_id)
        
        if not rating:
            # Если рейтинга нет, создаем с начальным значением
            rating = await rating_service.get_or_create_rating(target_type, target_id)
        
        # Получаем статистику
        statistics = await rating_service.get_rating_statistics(target_type, target_id)
        
        # Форматируем звездный рейтинг
        star_info = rating_service.get_star_rating(float(rating.average_rating))
        
        return JSONResponse(content={
            "success": True,
            "rating": {
                "id": rating.id,
                "target_type": rating.target_type,
                "target_id": rating.target_id,
                "average_rating": float(rating.average_rating),
                "total_reviews": rating.total_reviews,
                "last_updated": rating.last_updated.isoformat(),
                "stars": star_info,
                "statistics": statistics
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rating: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения рейтинга: {str(e)}")


@router.post("/{target_type}/{target_id}/recalculate")
async def recalculate_rating(
    request: Request,
    target_type: str,
    target_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Пересчет рейтинга (только для владельцев и администраторов).
    
    Args:
        target_type: Тип цели
        target_id: ID цели
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат пересчета
    """
    try:
        if target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Неподдерживаемый тип цели")
        
        rating_service = RatingService(db)
        
        # Пересчитываем рейтинг
        rating = await rating_service.calculate_rating(target_type, target_id)
        
        if not rating:
            raise HTTPException(status_code=500, detail="Ошибка пересчета рейтинга")
        
        star_info = rating_service.get_star_rating(float(rating.average_rating))
        
        logger.info(f"Recalculated rating for {target_type} {target_id} by user {current_user.get('id')}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Рейтинг успешно пересчитан",
            "rating": {
                "id": rating.id,
                "target_type": rating.target_type,
                "target_id": rating.target_id,
                "average_rating": float(rating.average_rating),
                "total_reviews": rating.total_reviews,
                "last_updated": rating.last_updated.isoformat(),
                "stars": star_info
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating rating: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка пересчета рейтинга: {str(e)}")


@router.post("/batch")
async def get_multiple_ratings(
    request: Request,
    targets: List[dict],
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение рейтингов для множественных целей.
    
    Args:
        targets: Список целей [{"target_type": "employee", "target_id": 1}, ...]
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Словарь рейтингов
    """
    try:
        if not targets or len(targets) > 100:
            raise HTTPException(status_code=400, detail="Количество целей должно быть от 1 до 100")
        
        # Валидируем и преобразуем цели
        validated_targets = []
        for target in targets:
            if not isinstance(target, dict) or 'target_type' not in target or 'target_id' not in target:
                raise HTTPException(status_code=400, detail="Неверный формат цели")
            
            target_type = target['target_type']
            target_id = target['target_id']
            
            if target_type not in ['employee', 'object']:
                raise HTTPException(status_code=400, detail="Неподдерживаемый тип цели")
            
            if not isinstance(target_id, int) or target_id <= 0:
                raise HTTPException(status_code=400, detail="Неверный ID цели")
            
            validated_targets.append((target_type, target_id))
        
        rating_service = RatingService(db)
        
        # Получаем рейтинги
        ratings = await rating_service.get_multiple_ratings(validated_targets)
        
        # Форматируем результат
        formatted_ratings = {}
        for (target_type, target_id), rating in ratings.items():
            key = f"{target_type}_{target_id}"
            star_info = rating_service.get_star_rating(float(rating.average_rating))
            formatted_ratings[key] = {
                "id": rating.id,
                "target_type": rating.target_type,
                "target_id": rating.target_id,
                "average_rating": float(rating.average_rating),
                "total_reviews": rating.total_reviews,
                "last_updated": rating.last_updated.isoformat(),
                "stars": star_info
            }
        
        return JSONResponse(content={
            "success": True,
            "ratings": formatted_ratings,
            "count": len(formatted_ratings)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting multiple ratings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения рейтингов: {str(e)}")


@router.get("/statistics/{target_type}/{target_id}")
async def get_rating_statistics(
    request: Request,
    target_type: str,
    target_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение детальной статистики рейтинга.
    
    Args:
        target_type: Тип цели
        target_id: ID цели
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Статистика рейтинга
    """
    try:
        if target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Неподдерживаемый тип цели")
        
        rating_service = RatingService(db)
        
        # Получаем статистику
        statistics = await rating_service.get_rating_statistics(target_type, target_id)
        
        # Получаем основной рейтинг
        rating = await rating_service.get_rating(target_type, target_id)
        if not rating:
            rating = await rating_service.get_or_create_rating(target_type, target_id)
        
        star_info = rating_service.get_star_rating(float(rating.average_rating))
        
        return JSONResponse(content={
            "success": True,
            "rating": {
                "id": rating.id,
                "target_type": rating.target_type,
                "target_id": rating.target_id,
                "average_rating": float(rating.average_rating),
                "total_reviews": rating.total_reviews,
                "last_updated": rating.last_updated.isoformat(),
                "stars": star_info
            },
            "statistics": statistics
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rating statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@router.post("/admin/recalculate-all")
async def recalculate_all_ratings(
    request: Request,
    target_type: Optional[str] = None,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Пересчет всех рейтингов (только для администраторов).
    
    Args:
        target_type: Тип цели для пересчета (опционально)
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат пересчета
    """
    try:
        if target_type and target_type not in ['employee', 'object']:
            raise HTTPException(status_code=400, detail="Неподдерживаемый тип цели")
        
        rating_service = RatingService(db)
        
        # Пересчитываем все рейтинги
        updated_count = await rating_service.recalculate_all_ratings(target_type)
        
        logger.info(f"Recalculated all ratings by user {current_user.get('id')}, updated: {updated_count}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Пересчитано {updated_count} рейтингов",
            "updated_count": updated_count,
            "target_type": target_type
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating all ratings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка пересчета рейтингов: {str(e)}")