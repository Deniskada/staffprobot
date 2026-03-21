"""
Сервис авторизации для веб-приложения
"""

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from core.config.settings import settings
from core.cache.cache_service import CacheService
from core.logging.logger import logger
from apps.web.services.bot_integration import BotIntegrationService
from domain.entities.user import UserRole

class AuthService:
    """Сервис авторизации с JWT токенами и PIN-кодами"""
    
    def __init__(self):
        self.cache = CacheService()
        self.bot_integration = BotIntegrationService()
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.token_expire_minutes = settings.jwt_expire_minutes
    
    async def create_token(self, user_data: Dict[str, Any]) -> str:
        """Создание JWT токена для пользователя"""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        
        payload = {
            "sub": str(user_data["id"]),
            "telegram_id": user_data.get("telegram_id"),
            "username": user_data.get("username"),
            "first_name": user_data["first_name"],
            "last_name": user_data.get("last_name"),
            "role": user_data["role"],
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Проверка и декодирование JWT токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return {
                "id": int(payload["sub"]),
                "telegram_id": payload.get("telegram_id", payload.get("id")),
                "username": payload.get("username"),
                "first_name": payload["first_name"],
                "last_name": payload.get("last_name"),
                "role": payload["role"]
            }
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def generate_and_send_pin(
        self, messenger: str, external_id: str
    ) -> str:
        """Генерация и отправка PIN-кода через бота. messenger: telegram|max."""
        pin_code = f"{secrets.randbelow(1000000):06d}"
        await self.store_pin(messenger, external_id, pin_code, ttl=300)
        success = await self.bot_integration.send_pin_code(messenger, external_id, pin_code)
        if not success:
            logger.warning(f"Failed to send PIN to {messenger}:{external_id}, code: {pin_code}")
            bot_hint = "Telegram" if messenger == "telegram" else "MAX"
            raise Exception(f"Не удалось отправить PIN. Откройте бота StaffProBot в {bot_hint} и нажмите Start.")
        return pin_code

    async def store_pin(
        self, messenger: str, external_id: str, pin_code: str, ttl: int = 300
    ) -> None:
        """Сохранение PIN-кода в кэше. key = pin:{messenger}:{external_id}."""
        key = f"pin:{messenger}:{external_id}"
        from datetime import timedelta
        await self.cache.set(key, pin_code, ttl=timedelta(seconds=ttl))

    async def verify_pin(self, messenger: str, external_id: str, pin_code: str) -> bool:
        """Проверка PIN-кода."""
        key = f"pin:{messenger}:{external_id}"
        stored_pin = await self.cache.get(key)
        logger.info(f"Verifying PIN for {messenger}:{external_id}: stored={bool(stored_pin)}, provided={bool(pin_code)}")
        if not stored_pin:
            return False
        if stored_pin == pin_code:
            logger.info(f"PIN verified for {messenger}:{external_id}")
            return True
        return False

    async def delete_pin(self, messenger: str, external_id: str) -> None:
        """Удаление PIN-кода из кэша (после успешного входа)."""
        key = f"pin:{messenger}:{external_id}"
        await self.cache.delete(key)
        logger.info(f"PIN deleted for {messenger}:{external_id} after login")
    
    async def refresh_token(self, token: str) -> Optional[str]:
        """Обновление JWT токена"""
        user_data = await self.verify_token(token)
        if not user_data:
            return None
        
        return await self.create_token(user_data)
    
    async def revoke_token(self, token: str) -> None:
        """Отзыв JWT токена (добавление в черный список)"""
        # TODO: Реализация черного списка токенов в Redis
        pass
    
    def has_role(self, user_data: Dict[str, Any], required_role: UserRole) -> bool:
        """Проверка, имеет ли пользователь указанную роль"""
        user_role = user_data.get("role", "employee")
        return user_role == required_role.value
    
    def has_any_role(self, user_data: Dict[str, Any], required_roles: List[UserRole]) -> bool:
        """Проверка, имеет ли пользователь любую из указанных ролей"""
        user_role = user_data.get("role", "employee")
        return user_role in [role.value for role in required_roles]
    
    def can_manage_objects(self, user_data: Dict[str, Any]) -> bool:
        """Проверка, может ли пользователь управлять объектами"""
        return self.has_any_role(user_data, [UserRole.OWNER, UserRole.SUPERADMIN])
    
    def can_manage_users(self, user_data: Dict[str, Any]) -> bool:
        """Проверка, может ли пользователь управлять пользователями"""
        return self.has_any_role(user_data, [UserRole.OWNER, UserRole.SUPERADMIN])
    
    def can_work_shifts(self, user_data: Dict[str, Any]) -> bool:
        """Проверка, может ли пользователь работать сменами"""
        return self.has_any_role(user_data, [UserRole.EMPLOYEE, UserRole.OWNER, UserRole.SUPERADMIN])
