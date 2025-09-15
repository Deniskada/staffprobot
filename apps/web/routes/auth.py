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
from core.logging.logger import logger

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
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "title": "Вход в систему",
                "error": "Неверный PIN-код или время истекло",
                "telegram_id": telegram_id,
                "pin_code": pin_code
            })
        
        # Получение пользователя
        logger.info(f"Getting user by telegram_id: {telegram_id}")
        user = await user_manager.get_user_by_telegram_id(telegram_id)
        logger.info(f"User found: {user is not None}")
        if not user:
            logger.warning(f"User not found for telegram_id: {telegram_id}")
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "title": "Вход в систему",
                "error": "Пользователь не найден",
                "telegram_id": telegram_id,
                "pin_code": pin_code
            })
        
        # Создание JWT токена с ролью из базы данных
        token = await auth_service.create_token({
            "id": user["id"],
            "telegram_id": user["telegram_id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "role": user.get("role", "employee")  # Роль из базы данных
        })
        
        # Перенаправление на дашборд с токеном
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=False)
        
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


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации собственника"""
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "title": "Регистрация собственника"
    })


@router.post("/register")
async def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    username: str = Form(...),
    telegram_id: int = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    terms: bool = Form(False)
):
    """Обработка регистрации собственника"""
    try:
        # Проверка согласия с условиями
        if not terms:
            return templates.TemplateResponse("auth/register.html", {
                "request": request,
                "title": "Регистрация собственника",
                "error": "Необходимо согласиться с условиями использования",
                "form_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "telegram_id": telegram_id,
                    "email": email,
                    "phone": phone,
                    "company_name": company_name
                }
            })
        
        # Проверка существования пользователя
        existing_user = await user_manager.get_user_by_telegram_id(telegram_id)
        if existing_user:
            return templates.TemplateResponse("auth/register.html", {
                "request": request,
                "title": "Регистрация собственника",
                "error": "Пользователь с таким Telegram ID уже зарегистрирован",
                "form_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "telegram_id": telegram_id,
                    "email": email,
                    "phone": phone,
                    "company_name": company_name
                }
            })
        
        # Создание пользователя
        user_data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "role": "owner",
            "is_active": True
        }
        
        # Добавляем название компании в дополнительные данные
        if company_name:
            user_data["company_name"] = company_name
        
        user = await user_manager.create_user(user_data)
        
        if not user:
            return templates.TemplateResponse("auth/register.html", {
                "request": request,
                "title": "Регистрация собственника",
                "error": "Ошибка создания пользователя",
                "form_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "telegram_id": telegram_id,
                    "email": email,
                    "phone": phone,
                    "company_name": company_name
                }
            })
        
        # Отправка PIN-кода для подтверждения
        try:
            pin_code = await auth_service.generate_and_send_pin(telegram_id)
            logger.info(f"PIN code sent to user {telegram_id} for registration")
        except Exception as e:
            logger.error(f"Failed to send PIN code: {e}")
            # Продолжаем без PIN-кода, пользователь может войти позже
        
        # Перенаправление на страницу входа с сообщением об успехе
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "title": "Вход в систему",
            "success": "Регистрация успешна! Проверьте Telegram для получения PIN-кода",
            "telegram_id": telegram_id
        })
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "title": "Регистрация собственника",
            "error": f"Ошибка регистрации: {str(e)}",
            "form_data": {
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "telegram_id": telegram_id,
                "email": email,
                "phone": phone,
                "company_name": company_name
            }
        })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Страница профиля пользователя"""
    # TODO: Получение текущего пользователя из токена
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "title": "Профиль пользователя"
    })
