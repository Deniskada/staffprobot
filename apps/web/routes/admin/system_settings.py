"""
API роуты для управления системными настройками
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any
from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.system_settings_service import SystemSettingsService
from core.utils.url_helper import URLHelper
from core.logging.logger import logger

router = APIRouter(prefix="/api/system-settings", tags=["system-settings"])


class DomainUpdateRequest(BaseModel):
    domain: str


class EmailUpdateRequest(BaseModel):
    email: str


class HTTPSUpdateRequest(BaseModel):
    use_https: bool


@router.get("/domain")
async def get_domain(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить текущий домен"""
    try:
        settings_service = SystemSettingsService(db)
        domain = await settings_service.get_domain()
        
        return {
            "domain": domain,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error getting domain: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения домена")


@router.post("/domain")
async def update_domain(
    request: DomainUpdateRequest,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновить домен"""
    try:
        settings_service = SystemSettingsService(db)
        
        # Валидируем домен
        validation_result = await settings_service.validate_domain(request.domain)
        if not validation_result["valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"]
            }
        
        # Обновляем домен
        success = await settings_service.set_domain(request.domain)
        
        if success:
            # Очищаем кэш URL
            await URLHelper.clear_cache()
            
            return {
                "success": True,
                "message": "Домен успешно обновлен",
                "domain": request.domain
            }
        else:
            return {
                "success": False,
                "message": "Ошибка обновления домена"
            }
            
    except Exception as e:
        logger.error(f"Error updating domain: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления домена")


@router.get("/domain/validate")
async def validate_domain(
    domain: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Валидация домена"""
    try:
        settings_service = SystemSettingsService(db)
        result = await settings_service.validate_domain(domain)
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating domain: {e}")
        raise HTTPException(status_code=500, detail="Ошибка валидации домена")


@router.get("/domain/preview")
async def preview_domain_config(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Предварительный просмотр конфигурации домена"""
    try:
        settings_service = SystemSettingsService(db)
        
        domain = await settings_service.get_domain()
        use_https = await settings_service.get_use_https()
        ssl_email = await settings_service.get_ssl_email()
        
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{domain}"
        
        config_preview = {
            "domain": domain,
            "protocol": protocol,
            "base_url": base_url,
            "web_url": f"{base_url}",
            "api_url": f"{base_url}/api",
            "admin_url": f"{base_url}/admin",
            "manager_url": f"{base_url}/manager",
            "employee_url": f"{base_url}/employee",
            "bot_webhook_url": f"{base_url}/webhook",
            "ssl_enabled": use_https,
            "ssl_email": ssl_email
        }
        
        return {
            "success": True,
            "config": config_preview
        }
        
    except Exception as e:
        logger.error(f"Error previewing domain config: {e}")
        raise HTTPException(status_code=500, detail="Ошибка предварительного просмотра")


@router.get("/ssl/email")
async def get_ssl_email(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить email для SSL"""
    try:
        settings_service = SystemSettingsService(db)
        email = await settings_service.get_ssl_email()
        
        return {
            "email": email,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error getting SSL email: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения email")


@router.post("/ssl/email")
async def update_ssl_email(
    request: EmailUpdateRequest,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновить email для SSL"""
    try:
        settings_service = SystemSettingsService(db)
        success = await settings_service.set_ssl_email(request.email)
        
        if success:
            return {
                "success": True,
                "message": "Email для SSL успешно обновлен",
                "email": request.email
            }
        else:
            return {
                "success": False,
                "message": "Ошибка обновления email"
            }
            
    except Exception as e:
        logger.error(f"Error updating SSL email: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления email")


@router.get("/https")
async def get_https_setting(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить настройку HTTPS"""
    try:
        settings_service = SystemSettingsService(db)
        use_https = await settings_service.get_use_https()
        
        return {
            "use_https": use_https,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error getting HTTPS setting: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения настройки HTTPS")


@router.post("/https")
async def update_https_setting(
    request: HTTPSUpdateRequest,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновить настройку HTTPS"""
    try:
        settings_service = SystemSettingsService(db)
        success = await settings_service.set_use_https(request.use_https)
        
        if success:
            # Очищаем кэш URL
            await URLHelper.clear_cache()
            
            return {
                "success": True,
                "message": "Настройка HTTPS успешно обновлена",
                "use_https": request.use_https
            }
        else:
            return {
                "success": False,
                "message": "Ошибка обновления настройки HTTPS"
            }
            
    except Exception as e:
        logger.error(f"Error updating HTTPS setting: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления настройки HTTPS")


@router.get("/all")
async def get_all_settings(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить все системные настройки"""
    try:
        settings_service = SystemSettingsService(db)
        settings = await settings_service.get_all_settings()
        
        return {
            "success": True,
            "settings": settings
        }
        
    except Exception as e:
        logger.error(f"Error getting all settings: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения настроек")


@router.post("/initialize")
async def initialize_settings(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Инициализировать настройки по умолчанию"""
    try:
        settings_service = SystemSettingsService(db)
        success = await settings_service.initialize_default_settings()
        
        if success:
            return {
                "success": True,
                "message": "Настройки по умолчанию инициализированы"
            }
        else:
            return {
                "success": False,
                "message": "Ошибка инициализации настроек"
            }
            
    except Exception as e:
        logger.error(f"Error initializing settings: {e}")
        raise HTTPException(status_code=500, detail="Ошибка инициализации настроек")


@router.post("/cache/clear")
async def clear_cache(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Очистить кэш настроек"""
    try:
        settings_service = SystemSettingsService(db)
        success = await settings_service.clear_cache()
        
        if success:
            # Также очищаем кэш URL
            await URLHelper.clear_cache()
            
            return {
                "success": True,
                "message": "Кэш успешно очищен"
            }
        else:
            return {
                "success": False,
                "message": "Ошибка очистки кэша"
            }
            
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Ошибка очистки кэша")
