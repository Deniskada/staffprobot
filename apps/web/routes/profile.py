"""
Роуты для управления профилем владельца.

Позволяет владельцу создавать и редактировать свой профиль
с динамическими тегами для использования в договорах.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.tag_service import TagService
from domain.entities.owner_profile import OwnerProfile
from domain.entities.tag_reference import TagReference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Страница профиля владельца."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        # Получаем внутренний user_id
        user_id = await get_user_id_from_current_user(current_user, session)
        
        # Получаем существующий профиль
        tag_service = TagService()
        profile = await tag_service.get_owner_profile(session, user_id)
        
        # Получаем все доступные теги
        all_tags = await tag_service.get_all_tags(session)
        
        # Группируем теги по категориям (для HTML)
        tags_by_category = {}
        # Группируем теги по категориям (для JSON)
        tags_by_category_json = {}
        
        for tag in all_tags:
            if tag.category not in tags_by_category:
                tags_by_category[tag.category] = []
                tags_by_category_json[tag.category] = []
            tags_by_category[tag.category].append(tag)
            tags_by_category_json[tag.category].append(tag.to_dict())
        
        return templates.TemplateResponse("profile/index.html", {
            "request": request,
            "current_user": current_user,
            "profile": profile,
            "tags_by_category": tags_by_category,
            "tags_by_category_json": tags_by_category_json,
            "legal_types": [
                {"value": "individual", "label": "Физическое лицо (ИП)"},
                {"value": "legal", "label": "Юридическое лицо (ООО)"}
            ]
        })


@router.post("/save")
async def save_profile(request: Request):
    """Сохранение профиля владельца."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем данные формы
    form_data = await request.form()
    
    async with get_async_session() as session:
        # Получаем внутренний user_id
        user_id = await get_user_id_from_current_user(current_user, session)
        
        # Извлекаем основные данные профиля
        profile_name = form_data.get("profile_name", "Мой профиль")
        legal_type = form_data.get("legal_type", "individual")
        is_public = form_data.get("is_public") == "on"
        
        # Извлекаем выбранные теги
        selected_tags = []
        for key, value in form_data.items():
            if key.startswith("tag_") and value == "on":
                tag_key = key[4:]  # убираем префикс "tag_"
                selected_tags.append(tag_key)
        
        # Извлекаем значения тегов
        profile_data = {}
        for key, value in form_data.items():
            if key.startswith("value_") and value.strip():
                tag_key = key[6:]  # убираем префикс "value_"
                if tag_key in selected_tags:  # только для выбранных тегов
                    profile_data[tag_key] = value.strip()
        
        # Сохраняем профиль
        tag_service = TagService()
        profile = await tag_service.create_or_update_owner_profile(
            session,
            user_id,
            {
                "profile_name": profile_name,
                "profile_data": profile_data,
                "active_tags": selected_tags,
                "is_public": is_public
            },
            legal_type
        )
        
        logger.info(f"Profile saved for user {user_id}: {len(selected_tags)} tags, {len(profile_data)} values")
        
        return RedirectResponse(url="/profile?success=1", status_code=303)


@router.get("/tags/{category}")
async def get_tags_by_category(request: Request, category: str):
    """API для получения тегов по категории."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        tag_service = TagService()
        tags = await tag_service.get_tags_by_category(session, category)
        
        return {
            "tags": [tag.to_dict() for tag in tags]
        }


@router.get("/preview")
async def profile_preview(request: Request):
    """Предпросмотр данных профиля для использования в договорах."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        # Получаем внутренний user_id
        user_id = await get_user_id_from_current_user(current_user, session)
        
        # Получаем профиль
        tag_service = TagService()
        profile = await tag_service.get_owner_profile(session, user_id)
        
        if not profile:
            return {"error": "Профиль не найден"}
        
        # Получаем все теги для подстановки в договоры
        tags_for_templates = profile.get_tags_for_templates()
        
        return {
            "profile": profile.to_dict(),
            "tags_for_templates": tags_for_templates,
            "completion": profile.get_completion_percentage()
        }


async def get_user_id_from_current_user(current_user, session):
    """Получает внутренний ID пользователя из current_user"""
    if isinstance(current_user, dict):
        # current_user - это словарь из JWT payload
        telegram_id = current_user.get("id")
        from domain.entities.user import User
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        # current_user - это объект User
        return current_user.id
