"""Middleware для контроля лимитов и платных функций."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import json

from core.database.session import get_async_session
from apps.web.services.limits_service import LimitsService
from core.logging.logger import logger


class LimitsMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматической проверки лимитов."""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Основная логика middleware."""
        if not self.enabled:
            return await call_next(request)
        
        # Получаем user_id из сессии или токена
        user_id = await self._get_user_id_from_request(request)
        if not user_id:
            return await call_next(request)
        
        # Проверяем лимиты для определенных эндпоинтов
        limits_check = await self._check_limits_for_endpoint(request, user_id)
        if not limits_check["allowed"]:
            return self._create_limits_error_response(limits_check["message"], limits_check["details"])
        
        response = await call_next(request)
        return response
    
    async def _get_user_id_from_request(self, request: Request) -> Optional[int]:
        """Получение user_id из запроса."""
        try:
            # Пытаемся получить из JWT токена
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                # TODO: Декодировать JWT и получить user_id
                pass
            
            # Пытаемся получить из сессии
            session_data = request.session
            if "user_id" in session_data:
                return session_data["user_id"]
            
            # Пытаемся получить из cookies
            user_id_cookie = request.cookies.get("user_id")
            if user_id_cookie:
                return int(user_id_cookie)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user_id from request: {e}")
            return None
    
    async def _check_limits_for_endpoint(self, request: Request, user_id: int) -> dict:
        """Проверка лимитов для конкретного эндпоинта."""
        try:
            path = request.url.path
            method = request.method
            
            # Определяем действие по пути и методу
            action = self._determine_action(path, method)
            if not action:
                return {"allowed": True, "message": "", "details": {}}
            
            # Проверяем лимиты
            async with get_async_session() as session:
                limits_service = LimitsService(session)
                
                if action == "create_object":
                    allowed, message, details = await limits_service.check_object_creation_limit(user_id)
                    return {"allowed": allowed, "message": message, "details": details}
                
                elif action == "add_employee":
                    # Получаем object_id из запроса
                    object_id = await self._get_object_id_from_request(request)
                    allowed, message, details = await limits_service.check_employee_creation_limit(user_id, object_id)
                    return {"allowed": allowed, "message": message, "details": details}
                
                elif action == "assign_manager":
                    allowed, message, details = await limits_service.check_manager_assignment_limit(user_id)
                    return {"allowed": allowed, "message": message, "details": details}
                
                elif action.startswith("use_feature_"):
                    feature = action.replace("use_feature_", "")
                    allowed, message, details = await limits_service.check_feature_access(user_id, feature)
                    return {"allowed": allowed, "message": message, "details": details}
                
                return {"allowed": True, "message": "", "details": {}}
                
        except Exception as e:
            logger.error(f"Error checking limits for endpoint {request.url.path}: {e}")
            return {"allowed": False, "message": "Ошибка проверки лимитов", "details": {}}
    
    def _determine_action(self, path: str, method: str) -> Optional[str]:
        """Определение действия по пути и методу запроса."""
        # Создание объектов
        if path.startswith("/owner/objects") and method == "POST":
            return "create_object"
        
        # Добавление сотрудников
        if path.startswith("/owner/employees") and method == "POST":
            return "add_employee"
        
        # Назначение управляющих
        if path.startswith("/owner/managers") and method == "POST":
            return "assign_manager"
        
        # Использование платных функций
        if path.startswith("/owner/analytics") or path.startswith("/owner/reports"):
            return "use_feature_analytics"
        
        if path.startswith("/owner/api/") and "export" in path:
            return "use_feature_export"
        
        if path.startswith("/owner/automation"):
            return "use_feature_automation"
        
        return None
    
    async def _get_object_id_from_request(self, request: Request) -> int:
        """Получение object_id из запроса."""
        try:
            # Пытаемся получить из query параметров
            object_id = request.query_params.get("object_id")
            if object_id:
                return int(object_id)
            
            # Пытаемся получить из path параметров
            path_parts = request.url.path.split("/")
            for i, part in enumerate(path_parts):
                if part == "objects" and i + 1 < len(path_parts):
                    try:
                        return int(path_parts[i + 1])
                    except ValueError:
                        continue
            
            # Пытаемся получить из body запроса
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        if "object_id" in data:
                            return int(data["object_id"])
                    except (json.JSONDecodeError, ValueError):
                        pass
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting object_id from request: {e}")
            return 0
    
    def _create_limits_error_response(self, message: str, details: dict) -> JSONResponse:
        """Создание ответа об ошибке лимитов."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "limits_exceeded",
                "message": message,
                "details": details,
                "upgrade_required": True
            }
        )


class LimitsDecorator:
    """Декоратор для проверки лимитов в роутах."""
    
    @staticmethod
    def check_object_limit(func):
        """Декоратор для проверки лимита объектов."""
        async def wrapper(*args, **kwargs):
            # TODO: Реализовать проверку лимита объектов
            return await func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def check_employee_limit(func):
        """Декоратор для проверки лимита сотрудников."""
        async def wrapper(*args, **kwargs):
            # TODO: Реализовать проверку лимита сотрудников
            return await func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def check_feature_access(feature: str):
        """Декоратор для проверки доступа к функции."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # TODO: Реализовать проверку доступа к функции
                return await func(*args, **kwargs)
            return wrapper
        return decorator


def create_limits_response(allowed: bool, message: str, details: dict = None) -> dict:
    """Создание стандартного ответа о лимитах."""
    from datetime import datetime, timezone
    return {
        "allowed": allowed,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
