import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from apps.web.services.system_settings_service import SystemSettingsService
from apps.web.services.ssl_service import SSLService
from core.logging.logger import logger
from core.cache.redis_cache import cache
import json

class SSLMonitoringService:
    """Сервис мониторинга SSL сертификатов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings_service = SystemSettingsService(session)
        self.ssl_service = SSLService(session)
    
    async def check_all_certificates(self) -> Dict[str, Any]:
        """
        Проверяет все SSL сертификаты в системе
        """
        logger.info("Starting SSL certificate monitoring check")
        
        try:
            # Получаем домен из настроек
            domain = await self.settings_service.get_domain()
            if not domain:
                return {
                    "status": "error",
                    "message": "No domain configured in system settings"
                }
            
            # Проверяем кэш
            cache_key = f"ssl_monitoring:{domain}"
            cached_result = await cache.get(cache_key)
            if cached_result:
                logger.info("Returning cached SSL monitoring result")
                return json.loads(cached_result)
            
            # Проверяем сертификат
            cert_info = await self.ssl_service.check_certificate_status(domain)
            
            # Анализируем результат
            monitoring_result = await self._analyze_certificate_status(domain, cert_info)
            
            # Кэшируем результат на 1 час
            await cache.set(cache_key, json.dumps(monitoring_result), ttl=3600)
            
            logger.info(f"SSL monitoring check completed for domain: {domain}")
            return monitoring_result
            
        except Exception as e:
            logger.error(f"Error in SSL monitoring check: {e}")
            return {
                "status": "error",
                "message": f"SSL monitoring check failed: {str(e)}"
            }
    
    async def _analyze_certificate_status(self, domain: str, cert_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует статус сертификата и определяет уровень критичности
        """
        result = {
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "certificate_info": cert_info,
            "status": "unknown",
            "criticality": "low",
            "recommendations": [],
            "alerts": []
        }
        
        if cert_info.get("status") == "error":
            result["status"] = "error"
            result["criticality"] = "high"
            result["alerts"].append({
                "type": "error",
                "message": f"Failed to check certificate for {domain}: {cert_info.get('message', 'Unknown error')}",
                "timestamp": datetime.now().isoformat()
            })
            result["recommendations"].append("Check SSL service configuration and certificate files")
            
        elif cert_info.get("status") == "not_found":
            result["status"] = "no_certificate"
            result["criticality"] = "high"
            result["alerts"].append({
                "type": "warning",
                "message": f"No SSL certificate found for {domain}",
                "timestamp": datetime.now().isoformat()
            })
            result["recommendations"].append("Set up SSL certificate using Let's Encrypt")
            
        elif cert_info.get("status") == "valid":
            days_remaining = cert_info.get("days_remaining", 0)
            
            if days_remaining <= 0:
                result["status"] = "expired"
                result["criticality"] = "critical"
                result["alerts"].append({
                    "type": "critical",
                    "message": f"SSL certificate for {domain} has expired",
                    "timestamp": datetime.now().isoformat()
                })
                result["recommendations"].append("Immediately renew SSL certificate")
                
            elif days_remaining <= 7:
                result["status"] = "expiring_soon"
                result["criticality"] = "high"
                result["alerts"].append({
                    "type": "warning",
                    "message": f"SSL certificate for {domain} expires in {days_remaining} days",
                    "timestamp": datetime.now().isoformat()
                })
                result["recommendations"].append("Renew SSL certificate as soon as possible")
                
            elif days_remaining <= 30:
                result["status"] = "expiring_soon"
                result["criticality"] = "medium"
                result["alerts"].append({
                    "type": "info",
                    "message": f"SSL certificate for {domain} expires in {days_remaining} days",
                    "timestamp": datetime.now().isoformat()
                })
                result["recommendations"].append("Schedule SSL certificate renewal")
                
            else:
                result["status"] = "healthy"
                result["criticality"] = "low"
                result["alerts"].append({
                    "type": "info",
                    "message": f"SSL certificate for {domain} is healthy ({days_remaining} days remaining)",
                    "timestamp": datetime.now().isoformat()
                })
        
        return result
    
    async def get_ssl_health_summary(self) -> Dict[str, Any]:
        """
        Получает краткую сводку о состоянии SSL
        """
        try:
            monitoring_result = await self.check_all_certificates()
            
            summary = {
                "overall_status": monitoring_result.get("status", "unknown"),
                "criticality": monitoring_result.get("criticality", "low"),
                "domain": monitoring_result.get("domain", "unknown"),
                "alerts_count": len(monitoring_result.get("alerts", [])),
                "recommendations_count": len(monitoring_result.get("recommendations", [])),
                "last_check": monitoring_result.get("timestamp", datetime.now().isoformat())
            }
            
            # Добавляем информацию о сертификате если доступна
            cert_info = monitoring_result.get("certificate_info", {})
            if cert_info.get("days_remaining") is not None:
                summary["days_remaining"] = cert_info["days_remaining"]
                summary["expiry_date"] = cert_info.get("expiry_date", "unknown")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting SSL health summary: {e}")
            return {
                "overall_status": "error",
                "criticality": "high",
                "domain": "unknown",
                "alerts_count": 1,
                "recommendations_count": 0,
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_ssl_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает список SSL алертов
        """
        try:
            monitoring_result = await self.check_all_certificates()
            alerts = monitoring_result.get("alerts", [])
            
            # Сортируем по типу критичности
            alert_priority = {"critical": 4, "error": 3, "warning": 2, "info": 1}
            alerts.sort(key=lambda x: alert_priority.get(x.get("type", "info"), 0), reverse=True)
            
            return alerts[:limit]
            
        except Exception as e:
            logger.error(f"Error getting SSL alerts: {e}")
            return [{
                "type": "error",
                "message": f"Failed to get SSL alerts: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }]
    
    async def get_ssl_recommendations(self) -> List[str]:
        """
        Получает рекомендации по SSL
        """
        try:
            monitoring_result = await self.check_all_certificates()
            return monitoring_result.get("recommendations", [])
            
        except Exception as e:
            logger.error(f"Error getting SSL recommendations: {e}")
            return [f"Error getting recommendations: {str(e)}"]
    
    async def force_ssl_renewal(self) -> Dict[str, Any]:
        """
        Принудительно обновляет SSL сертификаты
        """
        logger.info("Starting forced SSL certificate renewal")
        
        try:
            success, output = await self.ssl_service.renew_certificates()
            
            if success:
                # Очищаем кэш после успешного обновления
                domain = await self.settings_service.get_domain()
                if domain:
                    cache_key = f"ssl_monitoring:{domain}"
                    await cache.delete(cache_key)
                
                logger.info("SSL certificate renewal completed successfully")
                return {
                    "status": "success",
                    "message": "SSL certificates renewed successfully",
                    "output": output
                }
            else:
                logger.error(f"SSL certificate renewal failed: {output}")
                return {
                    "status": "error",
                    "message": "SSL certificate renewal failed",
                    "error": output
                }
                
        except Exception as e:
            logger.error(f"Error during forced SSL renewal: {e}")
            return {
                "status": "error",
                "message": f"SSL certificate renewal failed: {str(e)}"
            }
    
    async def get_ssl_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по SSL сертификатам
        """
        try:
            monitoring_result = await self.check_all_certificates()
            cert_info = monitoring_result.get("certificate_info", {})
            
            stats = {
                "domain": monitoring_result.get("domain", "unknown"),
                "status": monitoring_result.get("status", "unknown"),
                "criticality": monitoring_result.get("criticality", "low"),
                "last_check": monitoring_result.get("timestamp", datetime.now().isoformat()),
                "alerts_count": len(monitoring_result.get("alerts", [])),
                "recommendations_count": len(monitoring_result.get("recommendations", []))
            }
            
            # Добавляем информацию о сертификате
            if cert_info.get("days_remaining") is not None:
                stats["days_remaining"] = cert_info["days_remaining"]
                stats["expiry_date"] = cert_info.get("expiry_date", "unknown")
                stats["is_valid"] = cert_info.get("is_valid", False)
                
                # Вычисляем процент оставшегося времени
                if cert_info.get("days_remaining", 0) > 0:
                    # Предполагаем, что сертификат выдается на 90 дней
                    total_days = 90
                    remaining_days = cert_info["days_remaining"]
                    stats["renewal_percentage"] = min(100, max(0, (remaining_days / total_days) * 100))
                else:
                    stats["renewal_percentage"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting SSL statistics: {e}")
            return {
                "domain": "unknown",
                "status": "error",
                "criticality": "high",
                "last_check": datetime.now().isoformat(),
                "alerts_count": 1,
                "recommendations_count": 0,
                "error": str(e)
            }
