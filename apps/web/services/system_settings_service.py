"""
Сервис для управления системными настройками
"""

import socket
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from domain.entities.system_settings import SystemSettings
from domain.entities.settings_history import SettingsHistory
from core.cache.redis_cache import RedisCache
from core.logging.logger import logger


class SystemSettingsService:
    """Сервис для управления системными настройками"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = RedisCache()
        self.cache_key_prefix = "system_settings:"
        self.cache_ttl = 3600  # 1 час
    
    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Получить значение настройки по ключу"""
        try:
            # Сначала проверяем кэш
            cached_value = await self.cache.get(f"{self.cache_key_prefix}{key}")
            if cached_value is not None:
                return cached_value
            
            # Если нет в кэше, получаем из БД
            query = select(SystemSettings).where(SystemSettings.key == key)
            result = await self.db.execute(query)
            setting = result.scalar_one_or_none()
            
            if setting:
                value = setting.value
                # Кэшируем результат
                await self.cache.set(f"{self.cache_key_prefix}{key}", value, self.cache_ttl)
                return value
            
            return default
            
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    async def set_setting(self, key: str, value: str, description: Optional[str] = None, changed_by: str = None) -> bool:
        """Установить значение настройки"""
        try:
            # Проверяем, существует ли настройка
            query = select(SystemSettings).where(SystemSettings.key == key)
            result = await self.db.execute(query)
            existing_setting = result.scalar_one_or_none()
            
            old_value = existing_setting.value if existing_setting else None
            
            if existing_setting:
                # Обновляем существующую настройку
                update_query = (
                    update(SystemSettings)
                    .where(SystemSettings.key == key)
                    .values(value=value, description=description)
                )
                await self.db.execute(update_query)
            else:
                # Создаем новую настройку
                insert_query = insert(SystemSettings).values(
                    key=key,
                    value=value,
                    description=description
                )
                await self.db.execute(insert_query)
            
            await self.db.commit()
            
            # Логируем изменение, если значение изменилось
            logger.info(f"Setting change check: key={key}, old_value='{old_value}', new_value='{value}', changed={old_value != value}")
            if old_value != value:
                logger.info(f"Logging setting change: {key} from '{old_value}' to '{value}' by {changed_by}")
                await self.log_setting_change(
                    key=key,
                    old_value=old_value or "",
                    new_value=value,
                    changed_by=changed_by,
                    reason=f"Изменение настройки {key}"
                )
            else:
                logger.info(f"Setting {key} value unchanged, skipping history log")
            
            # Обновляем кэш
            await self.cache.set(f"{self.cache_key_prefix}{key}", value, self.cache_ttl)
            
            logger.info(f"Setting {key} updated to {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {key}={value}: {e}")
            await self.db.rollback()
            return False
    
    async def get_domain(self) -> str:
        """Получить домен системы"""
        return await self.get_setting("domain", "localhost:8001")
    
    async def set_domain(self, domain: str, changed_by: str = None) -> bool:
        """Установить домен системы"""
        # Валидируем домен
        if not self._validate_domain(domain):
            return False
        
        return await self.set_setting("domain", domain, "Основной домен системы", changed_by)
    
    async def get_ssl_email(self) -> str:
        """Получить email для SSL"""
        return await self.get_setting("ssl_email", "admin@localhost")
    
    async def set_ssl_email(self, email: str, changed_by: str = None) -> bool:
        """Установить email для SSL"""
        # Валидируем email
        if not self._validate_email(email):
            return False
        
        return await self.set_setting("ssl_email", email, "Email для Let's Encrypt сертификатов", changed_by)
    
    async def get_use_https(self) -> bool:
        """Получить настройку использования HTTPS"""
        value = await self.get_setting("use_https", "false")
        return value.lower() == "true"

    async def get_nginx_config_path(self) -> str:
        """Получить путь к конфигурации Nginx."""
        return await self.get_setting("nginx_config_path") or settings.nginx_config_path

    async def get_certbot_path(self) -> str:
        """Получить путь к исполняемому файлу Certbot."""
        return await self.get_setting("certbot_path") or settings.certbot_path
    
    async def set_use_https(self, use_https: bool, changed_by: str = None) -> bool:
        """Установить настройку использования HTTPS"""
        return await self.set_setting("use_https", str(use_https).lower(), "Использовать HTTPS", changed_by)

    # === Тестовые пользователи ===
    async def get_test_users_enabled(self) -> bool:
        """Включен ли режим тестовых пользователей"""
        value = await self.get_setting("enable_test_users", "false")
        return str(value).lower() == "true"

    async def set_test_users_enabled(self, enabled: bool, changed_by: str = None) -> bool:
        """Включить/выключить режим тестовых пользователей"""
        return await self.set_setting("enable_test_users", str(enabled).lower(), "Включить тестовых пользователей", changed_by)
    
    async def validate_domain(self, domain: str) -> Dict[str, Any]:
        """Валидация домена"""
        result = {
            "valid": False,
            "dns_resolves": False,
            "http_accessible": False,
            "errors": []
        }
        
        try:
            # Проверяем формат домена
            if not self._validate_domain(domain):
                result["errors"].append("Неверный формат домена")
                return result
            
            # Проверяем DNS
            try:
                socket.gethostbyname(domain)
                result["dns_resolves"] = True
            except socket.gaierror:
                result["errors"].append("Домен не резолвится в DNS")
                return result
            
            # Если DNS работает, считаем домен валидным
            result["valid"] = True
            
        except Exception as e:
            result["errors"].append(f"Ошибка валидации: {str(e)}")
        
        return result
    
    async def get_all_settings(self) -> Dict[str, str]:
        """Получить все настройки"""
        try:
            query = select(SystemSettings)
            result = await self.db.execute(query)
            settings = result.scalars().all()
            
            return {setting.key: setting.value for setting in settings}
            
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    async def initialize_default_settings(self) -> bool:
        """Инициализировать настройки по умолчанию"""
        try:
            default_settings = SystemSettings.get_default_settings()
            
            for key, value in default_settings.items():
                # Проверяем, существует ли настройка
                existing = await self.get_setting(key)
                if existing is None:
                    await self.set_setting(key, value, f"Настройка по умолчанию: {key}")
            
            logger.info("Default settings initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing default settings: {e}")
            return False
    
    def _validate_domain(self, domain: str) -> bool:
        """Валидация формата домена"""
        if not domain or len(domain) > 255:
            return False
        
        # Простая валидация домена
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, domain))
    
    def _validate_email(self, email: str) -> bool:
        """Валидация email"""
        if not email or len(email) > 254:
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    async def clear_cache(self) -> bool:
        """Очистить кэш настроек"""
        try:
            # Получаем все ключи настроек
            query = select(SystemSettings.key)
            result = await self.db.execute(query)
            keys = result.scalars().all()
            
            # Удаляем из кэша
            for key in keys:
                await self.cache.delete(f"{self.cache_key_prefix}{key}")
            
            logger.info("Settings cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    async def log_setting_change(self, key: str, old_value: str, new_value: str, changed_by: str = None, reason: str = None) -> None:
        """Логирование изменения настройки"""
        try:
            history_entry = SettingsHistory(
                setting_key=key,
                old_value=old_value,
                new_value=new_value,
                changed_by=changed_by,
                change_reason=reason
            )
            self.db.add(history_entry)
            await self.db.commit()
            logger.info(f"Setting change logged: {key} by {changed_by}")
        except Exception as e:
            logger.error(f"Error logging setting change: {e}")

    async def get_settings_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение истории изменений настроек"""
        try:
            query = select(SettingsHistory).order_by(SettingsHistory.created_at.desc()).limit(limit)
            result = await self.db.execute(query)
            history_entries = result.scalars().all()
            
            history = []
            for entry in history_entries:
                history.append({
                    "id": entry.id,
                    "setting_key": entry.setting_key,
                    "old_value": entry.old_value,
                    "new_value": entry.new_value,
                    "changed_by": entry.changed_by,
                    "change_reason": entry.change_reason,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None
                })
            
            return history
        except Exception as e:
            logger.error(f"Error getting settings history: {e}")
            return []
