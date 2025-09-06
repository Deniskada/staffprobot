"""
Роуты авторизации для веб-приложения
"""

from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import secrets
import asyncio

from core.auth.user_manager import UserManager
from apps.web.services.auth_service import AuthService

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

user_manager = UserManager()
auth_service = AuthService()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "title": "Вход в систему"
    })


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    telegram_id: int = Form(...),
    pin_code: str = Form(...)
):
    """Обработка входа по Telegram ID и PIN-коду"""
    try:
        # Проверка PIN-кода
        if not await auth_service.verify_pin(telegram_id, pin_code):
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "title": "Вход в систему",
                "error": "Неверный PIN-код или время истекло"
            })
        
        # Получение пользователя
        user = await user_manager.get_user_by_telegram_id(telegram_id)
        if not user:
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "title": "Вход в систему",
                "error": "Пользователь не найден"
            })
        
        # Создание JWT токена
        token = await auth_service.create_token({
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role
        })
        
        # Перенаправление на дашборд с токеном
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
        
        return response
        
    except Exception as e:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "title": "Вход в систему",
            "error": f"Ошибка входа: {str(e)}"
        })


@router.get("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


@router.post("/send-pin")
async def send_pin(telegram_id: int):
    """Отправка PIN-кода через бота"""
    try:
        # Генерация 6-значного PIN-кода
        pin_code = f"{secrets.randbelow(1000000):06d}"
        
        # Сохранение PIN-кода в Redis (действителен 5 минут)
        await auth_service.store_pin(telegram_id, pin_code, ttl=300)
        
        # Отправка через бота (здесь будет интеграция с ботом)
        # TODO: Интеграция с Telegram Bot API
        print(f"PIN для пользователя {telegram_id}: {pin_code}")
        
        return {"status": "success", "message": "PIN-код отправлен в Telegram"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Страница профиля пользователя"""
    # TODO: Получение текущего пользователя из токена
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "title": "Профиль пользователя"
    })
