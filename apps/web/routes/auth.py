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
from core.database.session import get_async_session
from sqlalchemy import select
from domain.entities.user import User, UserRole

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

user_manager = UserManager()
auth_service = AuthService()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    success_msg = request.query_params.get("success")
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "title": "Вход в систему",
        "success": success_msg
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
        "title": "Регистрация собственника",
        "form_data": {},
        "error": None,
        "success": None
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
    terms: Optional[str] = Form(None)
):
    """Обработка регистрации собственника"""
    try:
        # Проверка согласия с условиями
        # Чекбокс приходит как 'on' или не приходит вовсе
        if terms not in (True, 'on', 'true', '1'):
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
        async with get_async_session() as session:
            q = select(User).where(User.telegram_id == telegram_id)
            res = await session.execute(q)
            existing = res.scalar_one_or_none()
        if existing:
            # Апгрейдим до owner, если не владелец
            async with get_async_session() as session:
                if UserRole.OWNER.value not in (existing.roles or [existing.role]):
                    # Обновляем роль/роли
                    existing.role = UserRole.OWNER.value
                    existing.roles = list(set((existing.roles or []) + [UserRole.OWNER.value]))
                    session.add(existing)
                    await session.commit()
            # Отправляем PIN и редиректим на логин
            try:
                await auth_service.generate_and_send_pin(telegram_id)
            except Exception:
                pass
            return RedirectResponse(url=f"/auth/login?success=Пользователь%20обновлен.%20Проверьте%20Telegram%20для%20PIN&telegram_id={telegram_id}", status_code=status.HTTP_302_FOUND)
        
        # Создание пользователя в БД
        async with get_async_session() as session:
            new_user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=UserRole.OWNER.value,
                roles=[UserRole.OWNER.value],
                is_active=True,
            )
            session.add(new_user)
            await session.commit()
        
        # Отправка PIN-кода для подтверждения
        try:
            pin_code = await auth_service.generate_and_send_pin(telegram_id)
            logger.info(f"PIN code sent to user {telegram_id} for registration")
        except Exception as e:
            logger.error(f"Failed to send PIN code: {e}")
            # Продолжаем без PIN-кода, пользователь может войти позже
        
        # Перенаправление на страницу входа с сообщением об успехе
        return RedirectResponse(url=f"/auth/login?success=Регистрация%20успешна!%20Проверьте%20Telegram%20для%20получения%20PIN-кода&telegram_id={telegram_id}", status_code=status.HTTP_302_FOUND)
        
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
