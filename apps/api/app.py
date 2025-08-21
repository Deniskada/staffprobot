"""
FastAPI приложение StaffProBot
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import uuid

from core.config.settings import settings
from core.logging.logger import logger
from .main import api_router


def create_app() -> FastAPI:
    """Создание FastAPI приложения."""
    app = FastAPI(
        title=settings.app_name,
        description="API для управления сменами и объектами",
        version=settings.version,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # В продакшене ограничить
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # В продакшене ограничить
    )
    
    # Middleware для логирования запросов
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Логирование всех HTTP запросов."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Логируем начало запроса
        logger.info(
            "HTTP Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        try:
            response = await call_next(request)
            
            # Логируем успешное завершение
            process_time = time.time() - start_time
            logger.info(
                "HTTP Request completed",
                request_id=request_id,
                status_code=response.status_code,
                process_time=process_time
            )
            
            # Добавляем заголовки для отслеживания
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Логируем ошибки
            process_time = time.time() - start_time
            logger.error(
                "HTTP Request failed",
                request_id=request_id,
                error=str(e),
                process_time=process_time
            )
            raise
    
    # Обработчики ошибок
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Обработчик HTTP исключений."""
        logger.error(
            "HTTP Exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Обработчик ошибок валидации."""
        logger.error(
            "Validation Error",
            errors=exc.errors(),
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": "Ошибка валидации данных",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Общий обработчик исключений."""
        logger.error(
            "General Exception",
            error=str(exc),
            path=request.url.path,
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "Внутренняя ошибка сервера"
            }
        )
    
    # Подключаем API роутеры
    app.include_router(api_router)
    
    # Корневой эндпоинт
    @app.get("/")
    async def root():
        """Корневой эндпоинт."""
        return {
            "app": settings.app_name,
            "version": settings.version,
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled"
        }
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Проверка состояния приложения."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": settings.version
        }
    
    return app


# Создаем экземпляр приложения
app = create_app()

