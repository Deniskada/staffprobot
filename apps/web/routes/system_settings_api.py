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
from apps.web.services.nginx_service import NginxService
from apps.web.services.ssl_monitoring_service import SSLMonitoringService
from apps.web.services.ssl_logging_service import SSLLoggingService
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


@router.get("/nginx/preview")
async def preview_nginx_config(
    domain: str,
    use_https: bool,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Предварительный просмотр конфигурации Nginx."""
    try:
        nginx_service = NginxService(db)
        config_content = await nginx_service.generate_nginx_config(domain, use_https)
        return {"preview": config_content}
    except Exception as e:
        logger.error(f"Error generating Nginx config preview: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации предварительного просмотра: {str(e)}")


@router.post("/nginx/generate")
async def generate_nginx_config(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Генерация и сохранение конфигурации Nginx."""
    try:
        data = await request.json()
        domain = data.get("domain")
        use_https = data.get("use_https", False)
        
        if not domain:
            raise HTTPException(status_code=400, detail="Домен обязателен")
        
        nginx_service = NginxService(db)
        success = await nginx_service.save_nginx_config(domain, use_https)
        if success:
            return {"message": "Конфигурация Nginx сгенерирована успешно", "domain": domain}
        raise HTTPException(status_code=500, detail="Ошибка генерации конфигурации Nginx")
    except Exception as e:
        logger.error(f"Error generating Nginx config: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации конфигурации: {str(e)}")


@router.post("/nginx/validate")
async def validate_nginx_config(
    domain: str,
    use_https: bool,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Валидация конфигурации Nginx."""
    try:
        nginx_service = NginxService(db)
        validation_result = await nginx_service.validate_nginx_config(domain, use_https)
        return validation_result
    except Exception as e:
        logger.error(f"Error validating Nginx config: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка валидации конфигурации: {str(e)}")


@router.post("/nginx/apply")
async def apply_nginx_config(
    domain: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Применение конфигурации Nginx."""
    try:
        nginx_service = NginxService(db)
        success = await nginx_service.apply_nginx_config(domain)
        if success:
            return {"message": "Конфигурация Nginx применена успешно", "domain": domain}
        raise HTTPException(status_code=500, detail="Ошибка применения конфигурации Nginx")
    except Exception as e:
        logger.error(f"Error applying Nginx config: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка применения конфигурации: {str(e)}")


@router.get("/nginx/status")
async def get_nginx_status(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение статуса Nginx."""
    try:
        nginx_service = NginxService(db)
        status = await nginx_service.get_nginx_status()
        return status
    except Exception as e:
        logger.error(f"Error getting Nginx status: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса: {str(e)}")


@router.delete("/nginx/remove")
async def remove_nginx_config(
    domain: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление конфигурации Nginx."""
    try:
        nginx_service = NginxService(db)
        success = await nginx_service.remove_nginx_config(domain)
        if success:
            return {"message": "Конфигурация Nginx удалена успешно", "domain": domain}
        raise HTTPException(status_code=500, detail="Ошибка удаления конфигурации Nginx")
    except Exception as e:
        logger.error(f"Error removing Nginx config: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления конфигурации: {str(e)}")


@router.get("/nginx/backups")
async def list_nginx_backups(
    domain: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка backup'ов конфигурации Nginx."""
    try:
        nginx_service = NginxService(db)
        backups = await nginx_service.list_config_backups(domain)
        return {"backups": backups}
    except Exception as e:
        logger.error(f"Error listing Nginx backups: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения списка backup'ов: {str(e)}")


@router.post("/nginx/backups/restore")
async def restore_nginx_config_from_backup(
    domain: str,
    backup_filename: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Восстановление конфигурации Nginx из backup'а."""
    try:
        nginx_service = NginxService(db)
        success = await nginx_service.restore_config_from_backup(domain, backup_filename)
        if success:
            return {"message": f"Конфигурация Nginx восстановлена из backup: {backup_filename}", "domain": domain}
        raise HTTPException(status_code=500, detail="Ошибка восстановления конфигурации из backup")
    except Exception as e:
        logger.error(f"Error restoring Nginx config from backup: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка восстановления конфигурации: {str(e)}")


@router.delete("/nginx/backups/delete")
async def delete_nginx_backup(
    domain: str,
    backup_filename: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление backup'а конфигурации Nginx."""
    try:
        nginx_service = NginxService(db)
        success = await nginx_service.delete_config_backup(domain, backup_filename)
        if success:
            return {"message": f"Backup конфигурации Nginx удален: {backup_filename}", "domain": domain}
        raise HTTPException(status_code=500, detail="Ошибка удаления backup'а")
    except Exception as e:
        logger.error(f"Error deleting Nginx backup: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления backup'а: {str(e)}")


# SSL Monitoring endpoints
@router.get("/ssl/monitoring/status")
async def get_ssl_monitoring_status(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение статуса мониторинга SSL."""
    try:
        monitoring_service = SSLMonitoringService(db)
        result = await monitoring_service.check_all_certificates()
        return result
    except Exception as e:
        logger.error(f"Error getting SSL monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса мониторинга: {str(e)}")


@router.get("/ssl/monitoring/health")
async def get_ssl_health_summary(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение краткой сводки о состоянии SSL."""
    try:
        monitoring_service = SSLMonitoringService(db)
        summary = await monitoring_service.get_ssl_health_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting SSL health summary: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения сводки SSL: {str(e)}")


@router.get("/ssl/monitoring/alerts")
async def get_ssl_alerts(
    limit: int = 10,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка SSL алертов."""
    try:
        monitoring_service = SSLMonitoringService(db)
        alerts = await monitoring_service.get_ssl_alerts(limit)
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting SSL alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения алертов SSL: {str(e)}")


@router.get("/ssl/monitoring/recommendations")
async def get_ssl_recommendations(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение рекомендаций по SSL."""
    try:
        monitoring_service = SSLMonitoringService(db)
        recommendations = await monitoring_service.get_ssl_recommendations()
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Error getting SSL recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения рекомендаций SSL: {str(e)}")


@router.post("/ssl/monitoring/renew")
async def force_ssl_renewal(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Принудительное обновление SSL сертификатов."""
    try:
        monitoring_service = SSLMonitoringService(db)
        result = await monitoring_service.force_ssl_renewal()
        return result
    except Exception as e:
        logger.error(f"Error forcing SSL renewal: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка принудительного обновления SSL: {str(e)}")


@router.get("/ssl/monitoring/statistics")
async def get_ssl_statistics(
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение статистики по SSL сертификатам."""
    try:
        monitoring_service = SSLMonitoringService(db)
        stats = await monitoring_service.get_ssl_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting SSL statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики SSL: {str(e)}")


# SSL Logging endpoints
@router.get("/ssl/logs")
async def get_ssl_logs(
    domain: str = None,
    operation: str = None,
    status: str = None,
    days: int = 7,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение логов SSL операций."""
    try:
        logging_service = SSLLoggingService(db)
        logs = await logging_service.get_ssl_logs(
            domain=domain,
            operation=operation,
            status=status,
            days=days
        )
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting SSL logs: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения логов SSL: {str(e)}")


@router.get("/ssl/logs/statistics")
async def get_ssl_logs_statistics(
    domain: str = None,
    days: int = 30,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение статистики логов SSL."""
    try:
        logging_service = SSLLoggingService(db)
        statistics = await logging_service.get_ssl_statistics(domain=domain, days=days)
        return statistics
    except Exception as e:
        logger.error(f"Error getting SSL logs statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики логов: {str(e)}")


@router.get("/ssl/logs/errors")
async def get_recent_ssl_errors(
    domain: str = None,
    limit: int = 10,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение последних ошибок SSL."""
    try:
        logging_service = SSLLoggingService(db)
        errors = await logging_service.get_recent_ssl_errors(domain=domain, limit=limit)
        return {"errors": errors}
    except Exception as e:
        logger.error(f"Error getting recent SSL errors: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения ошибок SSL: {str(e)}")


@router.post("/ssl/logs/cleanup")
async def cleanup_ssl_logs(
    days_to_keep: int = 30,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Очистка старых логов SSL."""
    try:
        logging_service = SSLLoggingService(db)
        deleted_count = await logging_service.cleanup_old_logs(days_to_keep)
        return {"message": f"Удалено {deleted_count} старых файлов логов", "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Error cleaning up SSL logs: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки логов: {str(e)}")


@router.get("/ssl/logs/export")
async def export_ssl_logs(
    domain: str = None,
    days: int = 7,
    format: str = "json",
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Экспорт логов SSL."""
    try:
        logging_service = SSLLoggingService(db)
        exported_data = await logging_service.export_ssl_logs(
            domain=domain,
            days=days,
            format=format
        )
        
        if format == "json":
            return {"data": exported_data, "format": "json"}
        elif format == "csv":
            return {"data": exported_data, "format": "csv"}
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый формат экспорта")
            
    except Exception as e:
        logger.error(f"Error exporting SSL logs: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта логов: {str(e)}")


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
