"""
Веб-приложение StaffProBot
FastAPI приложение с Jinja2 шаблонами для управления объектами, сменами и договорами
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import Optional

from core.config.settings import settings
from core.auth.user_manager import UserManager
from apps.web.routes import auth, dashboard, objects, timeslots, calendar, shifts, reports, contracts, users, employees, templates as templates_routes, contract_templates, constructor_api, profile, admin, owner, employee, manager, manager_timeslots, test_calendar, notifications, tariffs, user_subscriptions, billing, limits, admin_reports, shared_media, shared_ratings, shared_appeals, shared_reviews, shared_cancellations, review_reports, moderator, moderator_web, owner_reviews, employee_reviews, manager_reviews, user_appeals, simple_test, manager_reviews_simple, test_dropdown, owner_shifts, owner_timeslots, payroll, payment_schedule, org_structure, manager_payroll, manager_payroll_adjustments, owner_payroll_adjustments, cancellations, admin_notifications, organization_profiles, owner_features, owner_media_storage, owner_cancellation_reasons, owner_rules, owner_tasks, owner_incidents, owner_products, manager_tasks, employee_tasks, employee_incidents, employee_offers, webhooks, owner_subscription, support, media_proxy, shared_profiles, address_book, manager_profiles
from routes.shared.calendar_api import router as calendar_api_router
from apps.web.routes.system_settings_api import router as system_settings_router
from core.database.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from apps.web.services.tariff_service import TariffService
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
    
    # Инициализация базы данных
    from core.database.session import init_database
    try:
        await init_database()
        print("✅ База данных подключена")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
    
    # Инициализация справочника тегов
    from apps.web.services.tag_service import TagService
    from core.database.session import get_async_session
    try:
        async with get_async_session() as session:
            tag_service = TagService()
            await tag_service.create_default_tags(session)
        print("✅ Справочник тегов инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации справочника тегов: {e}")
    
    # Инициализация системных настроек и URLHelper
    from apps.web.services.system_settings_service import SystemSettingsService
    from core.utils.url_helper import URLHelper
    try:
        async with get_async_session() as session:
            settings_service = SystemSettingsService(session)
            await settings_service.initialize_default_settings()
            URLHelper.set_settings_service(settings_service)
        print("✅ Системные настройки инициализированы")
    except Exception as e:
        print(f"❌ Ошибка инициализации системных настроек: {e}")
    
    yield
    
    # Очистка при завершении
    try:
        await cache.disconnect()
        print("✅ Redis отключен")
    except Exception as e:
        print(f"❌ Ошибка отключения от Redis: {e}")
    
    # Закрытие базы данных
    from core.database.session import close_database
    try:
        await close_database()
        print("✅ База данных отключена")
    except Exception as e:
        print(f"❌ Ошибка отключения от базы данных: {e}")
    
    print("🛑 Остановка веб-приложения StaffProBot")


# Создание FastAPI приложения
app = FastAPI(
    title="StaffProBot Web",
    description="Веб-интерфейс для управления объектами, сменами и договорами",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware для обработки заголовков прокси временно отключен
# from apps.web.middleware.proxy_middleware import ProxyMiddleware
# app.add_middleware(ProxyMiddleware)

# Настройка для работы за HTTPS
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["staffprobot.ru", "*.staffprobot.ru", "localhost", "127.0.0.1", "host.docker.internal"]
)

# Rate Limiting Middleware
from core.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# Features Middleware для автоматического добавления enabled_features
from apps.web.middleware.features_middleware import FeaturesMiddleware
app.add_middleware(FeaturesMiddleware)

# Middleware для принудительного HTTPS
@app.middleware("http")
async def force_https(request: Request, call_next):
    from core.logging.logger import logger
    
    # Логируем POST запросы к /shared/cancellations
    if request.method == "POST" and "/shared/cancellations" in request.url.path:
        logger.info(
            "HTTP middleware: POST to shared/cancellations",
            path=request.url.path,
            client=request.client.host if request.client else None,
        )
    
    # Проверяем заголовки от прокси (Nginx)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    # Устанавливаем HTTPS в scope для корректной генерации URL
    if forwarded_proto == "https" or request.url.scheme == "https":
        request.scope["scheme"] = "https"
        if forwarded_host:
            request.scope["server"] = (forwarded_host.split(":")[0], 443)
    
    response = await call_next(request)
    return response

# Настройка статических файлов
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")

# Настройка шаблонов: используем единый экземпляр
from apps.web.jinja import templates

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
async def root(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Главная страница - лендинг или перенаправление на дашборд"""
    # Проверяем, авторизован ли пользователь
    from apps.web.middleware.auth_middleware import get_current_user
    user_data = await get_current_user(request)
    
    if user_data:
        # Пользователь авторизован - перенаправляем в соответствующий раздел
        # Используем новую логику с множественными ролями
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Пользователь не авторизован - показываем лендинг
    try:
        tariff_service = TariffService(db)
        tariffs = await tariff_service.get_all_tariff_plans(active_only=True)
        
        # Загружаем системные функции для отображения названий
        from shared.services.system_features_service import SystemFeaturesService
        features_service = SystemFeaturesService()
        all_features = await features_service.get_all_features(db)
        feature_names_map = {f.key: f.name for f in all_features}
    except Exception:
        tariffs = []
        feature_names_map = {}
    
    return templates.TemplateResponse("landing.html", {
        "request": request, 
        "tariffs": tariffs,
        "feature_names": feature_names_map
    })


@app.get("/login")
async def login_redirect():
    """Редирект на страницу входа"""
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)


@app.get("/politic.html", response_class=HTMLResponse)
async def politic_page(request: Request):
    """Страница политики конфиденциальности"""
    from datetime import datetime
    return templates.TemplateResponse("politic.html", {
        "request": request,
        "title": "Политика конфиденциальности",
        "current_year": datetime.now().year
    })


@app.get("/test-page")
async def test_page():
    """Тестовая страница для проверки загрузки"""
    with open("test_simple_page.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


# Включение роутов
app.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Дашборд"])
# app.include_router(objects.router, prefix="/objects", tags=["Объекты"])  # Перенесено в owner.py
# app.include_router(timeslots.router, prefix="/timeslots", tags=["Тайм-слоты"])  # Перенесено в owner.py
# app.include_router(calendar.router, prefix="/calendar", tags=["Календарь"])  # Перенесено в owner.py
# app.include_router(shifts.router, prefix="/shifts", tags=["Смены"])  # Перенесено в owner.py
# app.include_router(reports.router, prefix="/reports", tags=["Отчеты"])  # Перенесено в owner.py
# app.include_router(contracts.router, prefix="/contracts", tags=["Договоры"])  # Перенесено в owner.py
app.include_router(users.router, prefix="/users", tags=["Пользователи"])
# app.include_router(employees.router, prefix="/employees", tags=["Сотрудники"])  # Перенесено в owner.py
# app.include_router(templates_routes.router, prefix="/templates", tags=["Шаблоны планирования"])  # Перенесено в owner.py
app.include_router(contract_templates.router, prefix="/owner/contract-templates", tags=["Шаблоны договоров"])
app.include_router(constructor_api.router, tags=["Конструктор шаблонов"])
# app.include_router(profile.router, tags=["Профиль владельца"])  # Перенесено в owner.py
app.include_router(admin.router, prefix="/admin", tags=["Администрирование"])
app.include_router(admin_notifications.router, prefix="/admin/notifications", tags=["Управление уведомлениями"])
app.include_router(system_settings_router, tags=["Системные настройки"])
app.include_router(tariffs.router, prefix="/admin/tariffs", tags=["Тарифные планы"])
app.include_router(user_subscriptions.router, prefix="/admin/subscriptions", tags=["Подписки пользователей"])
app.include_router(billing.router, prefix="/admin/billing", tags=["Система биллинга"])
app.include_router(limits.router, prefix="/owner/limits", tags=["Контроль лимитов"])
app.include_router(admin_reports.router, prefix="/admin/reports", tags=["Административные отчеты"])
# Специфичные роуты подключаем РАНЬШЕ общих для правильной маршрутизации
app.include_router(owner_timeslots.router, prefix="/owner/timeslots", tags=["Владелец - Тайм-слоты (новые)"])
app.include_router(owner_shifts.router, prefix="/owner/shifts", tags=["Владелец - Смены"])
app.include_router(cancellations.router, tags=["Отмена смен"])
app.include_router(media_proxy.router, tags=["Прокси медиа"])
app.include_router(owner_cancellation_reasons.router, tags=["Владелец - Причины отмен"])
app.include_router(owner_rules.router, tags=["Владелец - Правила"])
app.include_router(owner_tasks.router, tags=["Владелец - Задачи v2"])
app.include_router(owner_incidents.router, tags=["Владелец - Тикеты"])
app.include_router(owner_products.router, tags=["Владелец - Товары"])
app.include_router(owner_payroll_adjustments.router, prefix="/owner/payroll/adjustments", tags=["Владелец - Корректировки начислений"])
app.include_router(payroll.router, prefix="/owner", tags=["Владелец - Начисления и выплаты"])
app.include_router(payment_schedule.router, prefix="/owner", tags=["Владелец - Графики выплат"])
app.include_router(org_structure.router, prefix="/owner", tags=["Владелец - Организационная структура"])
app.include_router(organization_profiles.router, prefix="/owner/profile/organization", tags=["Владелец - Профили организаций"])
app.include_router(owner_features.router, prefix="/owner/profile/features", tags=["Владелец - Управление функциями"])
app.include_router(owner_media_storage.router, prefix="/owner/profile/media-storage", tags=["Владелец - Настройки хранилища"])
app.include_router(owner_subscription.router, prefix="/owner", tags=["Владелец - Подписки и платежи"])
app.include_router(owner.router, prefix="/owner", tags=["Владелец"])
app.include_router(manager.router, tags=["Управляющий"])
app.include_router(manager_tasks.router, tags=["Управляющий - Задачи v2"])
app.include_router(manager_payroll_adjustments.router, prefix="/manager/payroll/adjustments", tags=["Управляющий - Начисления"])
app.include_router(manager_payroll.router, prefix="/manager", tags=["Управляющий - Выплаты"])
app.include_router(manager_timeslots.router, tags=["Управляющий - Тайм-слоты"])
app.include_router(test_calendar.router, tags=["Тест календаря"])
app.include_router(employee.router, prefix="/employee", tags=["Сотрудник"])
app.include_router(employee_tasks.router, tags=["Сотрудник - Задачи v2"])
app.include_router(employee_incidents.router, tags=["Сотрудник - Тикеты"])
app.include_router(employee_offers.router, prefix="/employee", tags=["Сотрудник - Оферты"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Уведомления API"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Вебхуки"])
app.include_router(calendar_api_router, tags=["Календарь - API"])
app.include_router(shared_media.router, prefix="/api/media", tags=["Медиа-файлы"])
app.include_router(shared_ratings.router, prefix="/api/ratings", tags=["Рейтинги"])
app.include_router(moderator.router, prefix="/moderator/api", tags=["Модерация"])
app.include_router(moderator_web.router, prefix="/moderator", tags=["Модерация - Веб"])
app.include_router(shared_appeals.router, prefix="/api/appeals", tags=["Обжалования"])
app.include_router(shared_reviews.router, prefix="/api/reviews", tags=["Отзывы"])
app.include_router(shared_cancellations.router, prefix="/shared/cancellations", tags=["shared", "cancellations"])
app.include_router(review_reports.router, prefix="/api/reports/reviews", tags=["Отчеты - Отзывы"])
app.include_router(shared_profiles.router, tags=["Профили (shared API)"])
app.include_router(address_book.router, tags=["База адресов (shared API)"])
app.include_router(owner_reviews.router, prefix="/owner", tags=["Владелец - Отзывы"])
app.include_router(employee_reviews.router, prefix="/employee", tags=["Сотрудник - Отзывы"])
app.include_router(manager_reviews.router, prefix="/manager", tags=["Управляющий - Отзывы"])
app.include_router(user_appeals.router, tags=["Обжалования - Веб"])
app.include_router(simple_test.router, tags=["Простой тест"])
app.include_router(manager_reviews_simple.router, tags=["Управляющий - Отзывы (Простая версия)"])
app.include_router(test_dropdown.router, tags=["Тест Dropdown"])
app.include_router(support.router, prefix="/support", tags=["Поддержка"])
app.include_router(manager_profiles.router, prefix="/manager", tags=["Управляющий - Профили"])

from apps.web.routes.internal_api import router as internal_api_router
app.include_router(internal_api_router, tags=["Internal API"])


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
