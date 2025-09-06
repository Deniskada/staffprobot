"""
Веб-приложение StaffProBot
FastAPI приложение с Jinja2 шаблонами для управления объектами, сменами и договорами
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import Optional

from core.config.settings import settings
from core.auth.user_manager import UserManager
from apps.web.routes import auth, dashboard, objects, calendar, shifts, reports, contracts, users
from apps.web.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Инициализация при запуске
    print("🚀 Запуск веб-приложения StaffProBot")
    
    # Инициализация Redis
    from core.cache.redis_cache import cache
    try:
        await cache.connect()
        print("✅ Redis подключен")
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
    
    yield
    
    # Очистка при завершении
    try:
        await cache.disconnect()
        print("✅ Redis отключен")
    except Exception as e:
        print(f"❌ Ошибка отключения от Redis: {e}")
    
    print("🛑 Остановка веб-приложения StaffProBot")


# Создание FastAPI приложения
app = FastAPI(
    title="StaffProBot Web",
    description="Веб-интерфейс для управления объектами, сменами и договорами",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка статических файлов
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")

# Настройка шаблонов
templates = Jinja2Templates(directory="apps/web/templates")

# Инициализация сервисов
auth_service = AuthService()
user_manager = UserManager()

# Безопасность
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[dict]:
    """Получение текущего пользователя из JWT токена"""
    try:
        token = credentials.credentials
        user_data = await auth_service.verify_token(token)
        return user_data
    except Exception:
        return None


async def require_auth(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """Проверка авторизации пользователя"""
    if not current_user:
        # Перенаправление на страницу входа
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return current_user


async def require_role(required_role: str):
    """Декоратор для проверки роли пользователя"""
    async def role_checker(current_user: dict = Depends(require_auth)):
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав доступа"
            )
        return current_user
    return role_checker


# Главная страница
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница - перенаправление на дашборд или вход"""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "title": "StaffProBot",
        "page": "home"
    })


# Включение роутов
app.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Дашборд"])
app.include_router(objects.router, prefix="/objects", tags=["Объекты"])
app.include_router(calendar.router, prefix="/calendar", tags=["Календарь"])
app.include_router(shifts.router, prefix="/shifts", tags=["Смены"])
app.include_router(reports.router, prefix="/reports", tags=["Отчеты"])
app.include_router(contracts.router, prefix="/contracts", tags=["Договоры"])
app.include_router(users.router, prefix="/users", tags=["Пользователи"])


# API для интеграции с ботом
@app.post("/api/send-pin")
async def send_pin_api(request: Request):
    """API для отправки PIN-кода через бота"""
    try:
        # Получаем данные из тела запроса
        form_data = await request.form()
        print(f"Form data: {form_data}")
        telegram_id = int(form_data.get("telegram_id", 0))
        print(f"Telegram ID: {telegram_id}")
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID не указан")
        
        # Генерация и отправка PIN-кода
        pin_code = await auth_service.generate_and_send_pin(telegram_id)
        return {"status": "success", "message": "PIN-код отправлен в Telegram"}
        
    except ValueError as e:
        print(f"ValueError: {e}")
        raise HTTPException(status_code=400, detail="Неверный формат Telegram ID")
    except Exception as e:
        print(f"Exception: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/user/{telegram_id}")
async def get_user_by_telegram_id(telegram_id: int):
    """API для получения пользователя по Telegram ID"""
    try:
        user = await user_manager.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    """Проверка состояния приложения"""
    return {"status": "healthy", "service": "web"}


if __name__ == "__main__":
    uvicorn.run(
        "apps.web.app:app",
        host="0.0.0.0",
        port=8001,  # Отдельный порт для веб-приложения
        reload=True if settings.debug else False
    )
