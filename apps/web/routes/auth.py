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


@router.post("/login")
async def login(
    request: Request,
    telegram_id: int = Form(...),
    pin_code: str = Form(...)
):
    """Обработка входа по Telegram ID и PIN-коду"""
    try:
        # Проверка PIN-кода
        if not await auth_service.verify_pin(telegram_id, pin_code):
            if request.headers.get("hx-request"):
                return HTMLResponse("""
                    <div class="alert alert-danger" role="alert">
                        <i class="bi bi-exclamation-triangle"></i>
                        Неверный PIN-код или время истекло
                    </div>
                """)
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "title": "Вход в систему",
                "error": "Неверный PIN-код или время истекло"
            })
        
        # Получение пользователя
        user = await user_manager.get_user_by_telegram_id(telegram_id)
        if not user:
            if request.headers.get("hx-request"):
                return HTMLResponse("""
                    <div class="alert alert-danger" role="alert">
                        <i class="bi bi-exclamation-triangle"></i>
                        Пользователь не найден
                    </div>
                """)
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "title": "Вход в систему",
                "error": "Пользователь не найден"
            })
        
        # Создание JWT токена
        token = await auth_service.create_token({
            "id": user["id"],
            "telegram_id": user["id"],  # В UserManager id = telegram_id
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "role": "user"  # По умолчанию роль user
        })
        
        # Перенаправление на дашборд с токеном
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
        
        return response
        
    except Exception as e:
        if request.headers.get("hx-request"):
            return HTMLResponse(f"""
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle"></i>
                    Ошибка входа: {str(e)}
                </div>
            """)
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
async def send_pin(request: Request):
    """Отправка PIN-кода через бота"""
    try:
        # Получаем данные из тела запроса
        form_data = await request.form()
        telegram_id = int(form_data.get("telegram_id", 0))
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID не указан")
        
        # Генерация и отправка PIN-кода
        pin_code = await auth_service.generate_and_send_pin(telegram_id)
        
        return {"status": "success", "message": "PIN-код отправлен в Telegram"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат Telegram ID")
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
