"""
API endpoints для обжалований отзывов.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from shared.services.appeal_service import AppealService
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.logging.logger import logger
from typing import Optional, Dict, Any

router = APIRouter()


@router.post("/create")
async def create_appeal(
    request: Request,
    review_id: int = Form(...),
    appeal_reason: str = Form(...),
    evidence: Optional[str] = Form(None),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Создание обжалования отзыва.
    
    Args:
        review_id: ID отзыва
        appeal_reason: Причина обжалования
        evidence: Доказательства (JSON строка)
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Результат создания обжалования
    """
    try:
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_id = current_user.get('id')  # Telegram ID
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Проверяем возможность обжалования
        appeal_service = AppealService(db)
        appeal_check = await appeal_service.can_user_appeal_review(review_id, user_obj.id)
        
        if not appeal_check['can_appeal']:
            raise HTTPException(status_code=400, detail=appeal_check['reason'])
        
        # Парсим доказательства
        evidence_data = None
        if evidence:
            try:
                import json
                evidence_data = json.loads(evidence)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Неверный формат доказательств")
        
        # Создаем обжалование
        appeal = await appeal_service.create_appeal(
            review_id=review_id,
            appellant_id=user_obj.id,
            appeal_reason=appeal_reason,
            evidence=evidence_data
        )
        
        if not appeal:
            raise HTTPException(status_code=500, detail="Ошибка создания обжалования")
        
        logger.info(f"Appeal {appeal.id} created by user {user_obj.id} for review {review_id}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Обжалование успешно подано",
            "appeal": {
                "id": appeal.id,
                "review_id": appeal.review_id,
                "status": appeal.status,
                "created_at": appeal.created_at.isoformat()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating appeal: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания обжалования: {str(e)}")


@router.get("/check/{review_id}")
async def check_appeal_possibility(
    request: Request,
    review_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Проверка возможности обжалования отзыва.
    
    Args:
        review_id: ID отзыва
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Информация о возможности обжалования
    """
    try:
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_id = current_user.get('id')  # Telegram ID
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        appeal_service = AppealService(db)
        appeal_check = await appeal_service.can_user_appeal_review(review_id, user_obj.id)
        
        return JSONResponse(content={
            "success": True,
            "can_appeal": appeal_check['can_appeal'],
            "reason": appeal_check.get('reason'),
            "existing_appeals_count": appeal_check.get('existing_appeals_count', 0)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking appeal possibility: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка проверки возможности обжалования: {str(e)}")


@router.get("/my-appeals")
async def get_user_appeals(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение обжалований пользователя.
    
    Args:
        limit: Количество записей
        offset: Смещение
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список обжалований пользователя
    """
    try:
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_id = current_user.get('id')  # Telegram ID
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        appeal_service = AppealService(db)
        appeals = await appeal_service.get_user_appeals(user_obj.id, limit, offset)
        
        # Форматируем обжалования
        formatted_appeals = []
        for appeal in appeals:
            formatted_appeals.append({
                "id": appeal.id,
                "review_id": appeal.review_id,
                "appeal_reason": appeal.appeal_reason,
                "status": appeal.status,
                "moderator_decision": appeal.moderator_decision,
                "decision_notes": appeal.decision_notes,
                "created_at": appeal.created_at.isoformat(),
                "decided_at": appeal.decided_at.isoformat() if appeal.decided_at else None
            })
        
        return JSONResponse(content={
            "success": True,
            "appeals": formatted_appeals,
            "count": len(formatted_appeals)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user appeals: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения обжалований: {str(e)}")


@router.get("/details/{appeal_id}")
async def get_appeal_details(
    request: Request,
    appeal_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение детальной информации об обжаловании.
    
    Args:
        appeal_id: ID обжалования
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Детальная информация об обжаловании
    """
    try:
        appeal_service = AppealService(db)
        appeal_details = await appeal_service.get_appeal_details(appeal_id)
        
        if not appeal_details:
            raise HTTPException(status_code=404, detail="Обжалование не найдено")
        
        # Проверяем права доступа (пользователь может видеть только свои обжалования)
        user_id = current_user.get('id')  # Telegram ID
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj or appeal_details['appeal']['appellant_id'] != user_obj.id:
            raise HTTPException(status_code=403, detail="Нет прав доступа к этому обжалованию")
        
        return JSONResponse(content={
            "success": True,
            "appeal_details": appeal_details
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appeal details: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения деталей обжалования: {str(e)}")


@router.get("/statistics")
async def get_appeal_statistics(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение статистики обжалований (только для владельцев и администраторов).
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Статистика обжалований
    """
    try:
        appeal_service = AppealService(db)
        statistics = await appeal_service.get_appeal_statistics()
        
        return JSONResponse(content={
            "success": True,
            "statistics": statistics
        })
        
    except Exception as e:
        logger.error(f"Error getting appeal statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@router.get("/pending")
async def get_pending_appeals(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение обжалований, ожидающих рассмотрения (только для владельцев и администраторов).
    
    Args:
        limit: Количество записей
        offset: Смещение
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        JSONResponse: Список обжалований на рассмотрении
    """
    try:
        appeal_service = AppealService(db)
        appeals = await appeal_service.get_pending_appeals(limit, offset)
        
        # Форматируем обжалования
        formatted_appeals = []
        for appeal in appeals:
            formatted_appeals.append({
                "id": appeal.id,
                "review_id": appeal.review_id,
                "appellant_id": appeal.appellant_id,
                "appeal_reason": appeal.appeal_reason,
                "appeal_evidence": appeal.appeal_evidence,
                "status": appeal.status,
                "created_at": appeal.created_at.isoformat(),
                "days_pending": (datetime.utcnow() - appeal.created_at).days
            })
        
        return JSONResponse(content={
            "success": True,
            "appeals": formatted_appeals,
            "count": len(formatted_appeals)
        })
        
    except Exception as e:
        logger.error(f"Error getting pending appeals: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения обжалований: {str(e)}")


@router.post("/{appeal_id}/review")
async def review_appeal(
    request: Request,
    appeal_id: int,
    decision: str = Form(...),
    decision_notes: Optional[str] = Form(None),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Рассмотрение обжалования (только для владельцев и администраторов).
    
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
        
        # Получаем внутренний ID пользователя
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_id = current_user.get('id')  # Telegram ID
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        appeal_service = AppealService(db)
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
            "decision": decision
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing appeal: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка рассмотрения обжалования: {str(e)}")
