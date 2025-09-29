"""
Утилита для динамической генерации URL
"""

from typing import Optional
from core.cache.redis_cache import RedisCache
from core.logging.logger import logger


class URLHelper:
    """Утилита для генерации URL"""
    
    _cache = RedisCache()
    _cache_ttl = 3600  # 1 час
    _settings_service = None
    
    @classmethod
    def set_settings_service(cls, service):
        """Установить сервис настроек"""
        cls._settings_service = service
    
    @classmethod
    async def get_base_url(cls) -> str:
        """Получить базовый URL системы"""
        try:
            if not cls._settings_service:
                logger.warning("URLHelper: SystemSettingsService not set, using default localhost:8001")
                return "http://localhost:8001"
            
            # Получаем домен и настройку HTTPS
            domain = await cls._settings_service.get_domain()
            use_https = await cls._settings_service.get_use_https()
            
            logger.info(f"URLHelper: domain={domain}, use_https={use_https}")
            
            protocol = "https" if use_https else "http"
            
            # Обрабатываем случай с портом в домене
            if ":" in domain and not domain.startswith("http"):
                result = f"{protocol}://{domain}"
            elif domain.startswith("http"):
                result = domain
            else:
                result = f"{protocol}://{domain}"
            
            logger.info(f"URLHelper: returning base_url={result}")
            return result
            
        except Exception as e:
            logger.error(f"URLHelper: Error getting base URL: {e}")
            return "http://localhost:8001"
    
    @classmethod
    async def get_web_url(cls) -> str:
        """Получить URL веб-интерфейса"""
        base_url = await cls.get_base_url()
        return base_url
    
    @classmethod
    async def get_api_url(cls) -> str:
        """Получить URL API"""
        base_url = await cls.get_base_url()
        return f"{base_url}/api"
    
    @classmethod
    async def get_bot_webhook_url(cls) -> str:
        """Получить URL webhook для бота"""
        base_url = await cls.get_base_url()
        return f"{base_url}/webhook"
    
    @classmethod
    async def get_admin_url(cls) -> str:
        """Получить URL админ-панели"""
        base_url = await cls.get_base_url()
        return f"{base_url}/admin"
    
    @classmethod
    async def get_manager_url(cls) -> str:
        """Получить URL интерфейса управляющего"""
        base_url = await cls.get_base_url()
        return f"{base_url}/manager"
    
    @classmethod
    async def get_employee_url(cls) -> str:
        """Получить URL интерфейса сотрудника"""
        base_url = await cls.get_base_url()
        return f"{base_url}/employee"
    
    @classmethod
    async def get_owner_url(cls) -> str:
        """Получить URL интерфейса владельца"""
        base_url = await cls.get_base_url()
        return f"{base_url}/owner"
    
    @classmethod
    async def get_moderator_url(cls) -> str:
        """Получить URL интерфейса модератора"""
        base_url = await cls.get_base_url()
        return f"{base_url}/moderator"
    
    @classmethod
    async def get_domain_only(cls) -> str:
        """Получить только домен без протокола"""
        try:
            if not cls._settings_service:
                return "localhost:8001"
            
            domain = await cls._settings_service.get_domain()
            
            # Убираем протокол если есть
            if domain.startswith("http://"):
                return domain[7:]
            elif domain.startswith("https://"):
                return domain[8:]
            
            return domain
            
        except Exception as e:
            logger.error(f"Error getting domain: {e}")
            return "localhost:8001"
    
    @classmethod
    async def get_protocol(cls) -> str:
        """Получить протокол (http/https)"""
        try:
            if not cls._settings_service:
                return "http"
            
            use_https = await cls._settings_service.get_use_https()
            return "https" if use_https else "http"
            
        except Exception as e:
            logger.error(f"Error getting protocol: {e}")
            return "http"
    
    @classmethod
    async def build_url(cls, path: str = "") -> str:
        """Построить URL с указанным путем"""
        base_url = await cls.get_base_url()
        
        # Убираем ведущий слеш если есть
        if path.startswith("/"):
            path = path[1:]
        
        if path:
            return f"{base_url}/{path}"
        else:
            return base_url
    
    @classmethod
    async def clear_cache(cls) -> bool:
        """Очистить кэш URL"""
        try:
            # Очищаем кэш настроек, что приведет к пересчету URL
            if cls._settings_service:
                await cls._settings_service.clear_cache()
            
            logger.info("URL cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing URL cache: {e}")
            return False
