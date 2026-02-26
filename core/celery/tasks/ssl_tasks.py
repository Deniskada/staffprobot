"""
Celery задачи для управления SSL сертификатами
"""

from celery import Celery
from datetime import datetime, timedelta
from typing import Dict, Any
from core.logging.logger import logger
from core.database.session import get_celery_session
from apps.web.services.system_settings_service import SystemSettingsService
from apps.web.services.ssl_service import SSLService
from shared.services.notification_service import NotificationService

# Получаем экземпляр Celery
from core.celery.celery_app import celery_app


async def _renew_ssl_certificates_async() -> Dict[str, Any]:
    """Асинхронная функция обновления SSL сертификатов"""
    try:
        logger.info("Starting SSL certificate renewal task")
        
        async with get_celery_session() as session:
            settings_service = SystemSettingsService(session)
            ssl_service = SSLService(settings_service)
            
            # Получаем текущий домен
            domain = await settings_service.get_domain()
            if not domain or domain == "localhost:8001":
                logger.info("No production domain configured, skipping SSL renewal")
                return {
                    "success": True,
                    "message": "No production domain configured",
                    "skipped": True
                }
            
            # Проверяем, нужно ли обновление
            renewal_check = await ssl_service._check_renewal_needed()
            if not renewal_check["needed"]:
                logger.info("SSL certificate renewal not needed")
                return {
                    "success": True,
                    "message": "Certificate renewal not needed",
                    "next_check": datetime.now() + timedelta(days=1)
                }
            
            # Выполняем обновление
            result = await ssl_service.renew_certificates()
            
            if result["success"]:
                logger.info("SSL certificates renewed successfully")
                
                # Отправляем уведомление об успешном обновлении
                await _send_ssl_notification(
                    "success",
                    f"SSL сертификаты для {domain} успешно обновлены",
                    {"domain": domain, "renewed_at": datetime.now().isoformat()}
                )
                
                return result
            else:
                logger.error(f"SSL certificate renewal failed: {result.get('error', 'Unknown error')}")
                
                # Отправляем уведомление об ошибке
                await _send_ssl_notification(
                    "error",
                    f"Ошибка обновления SSL сертификатов для {domain}",
                    {"domain": domain, "error": result.get("error", "Unknown error")}
                )
                
                return result
                
    except Exception as e:
        logger.error(f"Error in SSL certificate renewal task: {e}")
        
        # Отправляем уведомление об ошибке
        await _send_ssl_notification(
            "error",
            f"Критическая ошибка в задаче обновления SSL сертификатов: {str(e)}",
            {"error": str(e), "task": "renew_ssl_certificates"}
        )
        
        return {
            "success": False,
            "error": f"Task execution error: {str(e)}"
        }


@celery_app.task(name="renew_ssl_certificates")
def renew_ssl_certificates() -> Dict[str, Any]:
    """Периодическая проверка и обновление SSL сертификатов"""
    import asyncio
    return asyncio.run(_renew_ssl_certificates_async())


async def _check_certificate_expiry_async() -> Dict[str, Any]:
    """Асинхронная функция проверки срока действия сертификатов"""
    try:
        logger.info("Starting SSL certificate expiry check task")
        
        async with get_celery_session() as session:
            settings_service = SystemSettingsService(session)
            ssl_service = SSLService(settings_service)
            
            # Получаем текущий домен
            domain = await settings_service.get_domain()
            if not domain or domain == "localhost:8001":
                logger.info("No production domain configured, skipping SSL check")
                return {
                    "success": True,
                    "message": "No production domain configured",
                    "skipped": True
                }
            
            # Проверяем статус сертификата
            status = await ssl_service.check_certificate_status(domain)
            
            if not status["valid"]:
                logger.error(f"SSL certificate is invalid for {domain}")
                await _send_ssl_notification(
                    "error",
                    f"SSL сертификат для {domain} невалиден",
                    {"domain": domain, "status": status}
                )
                return status
            
            # Проверяем срок действия
            days_until_expiry = status.get("days_until_expiry", 0)
            
            if days_until_expiry <= 0:
                logger.error(f"SSL certificate for {domain} has expired")
                await _send_ssl_notification(
                    "error",
                    f"SSL сертификат для {domain} истек!",
                    {"domain": domain, "expired": True}
                )
            elif days_until_expiry <= 7:
                logger.warning(f"SSL certificate for {domain} expires in {days_until_expiry} days")
                await _send_ssl_notification(
                    "warning",
                    f"SSL сертификат для {domain} истекает через {days_until_expiry} дней",
                    {"domain": domain, "days_until_expiry": days_until_expiry}
                )
            elif days_until_expiry <= 30:
                logger.info(f"SSL certificate for {domain} expires in {days_until_expiry} days")
                await _send_ssl_notification(
                    "info",
                    f"SSL сертификат для {domain} истекает через {days_until_expiry} дней",
                    {"domain": domain, "days_until_expiry": days_until_expiry}
                )
            else:
                logger.info(f"SSL certificate for {domain} is valid for {days_until_expiry} days")
            
            return {
                "success": True,
                "domain": domain,
                "days_until_expiry": days_until_expiry,
                "needs_renewal": days_until_expiry <= 30,
                "status": status
            }
            
    except Exception as e:
        logger.error(f"Error in SSL certificate expiry check task: {e}")
        
        # Отправляем уведомление об ошибке
        await _send_ssl_notification(
            "error",
            f"Ошибка проверки срока действия SSL сертификатов: {str(e)}",
            {"error": str(e), "task": "check_certificate_expiry"}
        )
        
        return {
            "success": False,
            "error": f"Task execution error: {str(e)}"
        }


@celery_app.task(name="check_certificate_expiry")
def check_certificate_expiry() -> Dict[str, Any]:
    """Проверка срока действия сертификатов"""
    import asyncio
    return asyncio.run(_check_certificate_expiry_async())


@celery_app.task
async def setup_ssl_for_domain(domain: str, email: str) -> Dict[str, Any]:
    """Настройка SSL для нового домена"""
    try:
        logger.info(f"Starting SSL setup task for domain: {domain}")
        
        async with get_celery_session() as session:
            settings_service = SystemSettingsService(session)
            ssl_service = SSLService(settings_service)
            
            # Выполняем настройку SSL
            result = await ssl_service.setup_ssl(domain, email)
            
            if result["success"]:
                logger.info(f"SSL setup completed successfully for {domain}")
                
                # Отправляем уведомление об успешной настройке
                await _send_ssl_notification(
                    "success",
                    f"SSL успешно настроен для домена {domain}",
                    {"domain": domain, "email": email, "setup_at": datetime.now().isoformat()}
                )
            else:
                logger.error(f"SSL setup failed for {domain}: {result.get('error', 'Unknown error')}")
                
                # Отправляем уведомление об ошибке
                await _send_ssl_notification(
                    "error",
                    f"Ошибка настройки SSL для домена {domain}",
                    {"domain": domain, "email": email, "error": result.get("error", "Unknown error")}
                )
            
            return result
            
    except Exception as e:
        logger.error(f"Error in SSL setup task for {domain}: {e}")
        
        # Отправляем уведомление об ошибке
        await _send_ssl_notification(
            "error",
            f"Критическая ошибка настройки SSL для {domain}: {str(e)}",
            {"domain": domain, "email": email, "error": str(e)}
        )
        
        return {
            "success": False,
            "error": f"Task execution error: {str(e)}"
        }


async def _validate_ssl_configuration_async() -> Dict[str, Any]:
    """Асинхронная функция валидации SSL конфигурации"""
    try:
        logger.info("Starting SSL configuration validation task")
        
        async with get_celery_session() as session:
            settings_service = SystemSettingsService(session)
            ssl_service = SSLService(settings_service)
            
            # Получаем текущий домен
            domain = await settings_service.get_domain()
            if not domain or domain == "localhost:8001":
                return {
                    "success": True,
                    "message": "No production domain configured",
                    "skipped": True
                }
            
            # Проверяем статус сертификата
            cert_status = await ssl_service.check_certificate_status(domain)
            
            # Проверяем конфигурацию nginx
            nginx_check = await ssl_service._reload_nginx()
            
            # Проверяем доступность сайта
            import aiohttp
            try:
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(f"https://{domain}", timeout=10) as response:
                        site_accessible = response.status == 200
            except Exception:
                site_accessible = False
            
            result = {
                "success": cert_status["valid"] and nginx_check["success"] and site_accessible,
                "domain": domain,
                "certificate": cert_status,
                "nginx": nginx_check,
                "site_accessible": site_accessible,
                "checked_at": datetime.now().isoformat()
            }
            
            if not result["success"]:
                logger.warning(f"SSL configuration validation failed for {domain}")
                await _send_ssl_notification(
                    "warning",
                    f"Проблемы с SSL конфигурацией для {domain}",
                    result
                )
            else:
                logger.info(f"SSL configuration validation passed for {domain}")
            
            return result
            
    except Exception as e:
        logger.error(f"Error in SSL configuration validation task: {e}")
        
        return {
            "success": False,
            "error": f"Task execution error: {str(e)}"
        }


@celery_app.task(name="validate_ssl_configuration")
def validate_ssl_configuration() -> Dict[str, Any]:
    """Валидация SSL конфигурации"""
    import asyncio
    return asyncio.run(_validate_ssl_configuration_async())


async def _send_ssl_notification(notification_type: str, message: str, data: Dict[str, Any]) -> None:
    """Отправка уведомления о SSL"""
    try:
        from domain.entities.user import User, UserRole
        from domain.entities.notification import NotificationType, NotificationChannel, NotificationPriority
        from sqlalchemy import select, or_
        
        async with get_celery_session() as session:
            notification_service = NotificationService()
            
            # Находим всех суперадминов
            roles_filter = User.roles.contains([UserRole.SUPERADMIN.value])
            query = select(User.id).where(
                or_(User.role == UserRole.SUPERADMIN.value, roles_filter)
            )
            result = await session.execute(query)
            superadmin_ids = [row[0] for row in result.fetchall()]
            
            if not superadmin_ids:
                logger.warning("No superadmins found for SSL notification")
                return
            
            # Определяем приоритет и тип уведомления
            priority = NotificationPriority.URGENT if notification_type == "error" else NotificationPriority.HIGH
            notif_type = NotificationType.SYSTEM_MAINTENANCE
            
            # Отправляем уведомления всем суперадминам
            for user_id in superadmin_ids:
                await notification_service.create_notification(
                    user_id=user_id,
                    type=notif_type,
                    channel=NotificationChannel.IN_APP,
                    title=f"SSL Alert: {notification_type.upper()}",
                    message=message,
                    data=data,
                    priority=priority
                )
                # Также отправляем в Telegram
                await notification_service.create_notification(
                    user_id=user_id,
                    type=notif_type,
                    channel=NotificationChannel.TELEGRAM,
                    title=f"SSL Alert: {notification_type.upper()}",
                    message=message,
                    data=data,
                    priority=priority
                )
            
            logger.info(f"SSL notification sent to {len(superadmin_ids)} superadmins: {notification_type}")
            
    except Exception as e:
        logger.error(f"Error sending SSL notification: {e}")


# Периодические задачи регистрируются в celery_app.py в beat_schedule
# Функция schedule_ssl_tasks() больше не используется, так как задачи
# автоматически планируются через beat_schedule
