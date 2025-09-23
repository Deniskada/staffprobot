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
            "telegram_id": user_data["telegram_id"],
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
    
    async def generate_and_send_pin(self, telegram_id: int) -> str:
        """Генерация и отправка PIN-кода через бота"""
        # Генерация 6-значного PIN-кода
        pin_code = f"{secrets.randbelow(1000000):06d}"
        
        # Сохранение PIN-кода в кэше (действителен 5 минут)
        await self.store_pin(telegram_id, pin_code, ttl=300)
        
        # Отправка PIN-кода через бота
        success = await self.bot_integration.send_pin_code(telegram_id, pin_code)
        
        if not success:
            # Если не удалось отправить через бота, логируем для отладки
            logger.warning(f"Failed to send PIN code to user {telegram_id}, code: {pin_code}")
        
        return pin_code
    
    async def store_pin(self, telegram_id: int, pin_code: str, ttl: int = 300) -> None:
        """Сохранение PIN-кода в кэше"""
        key = f"pin:{telegram_id}"
        from datetime import timedelta
        await self.cache.set(key, pin_code, ttl=timedelta(seconds=ttl))
    
    async def verify_pin(self, telegram_id: int, pin_code: str) -> bool:
        """Проверка PIN-кода"""
        key = f"pin:{telegram_id}"
        stored_pin = await self.cache.get(key)
        
        logger.info(f"Verifying PIN for user {telegram_id}: stored={stored_pin}, provided={pin_code}")
        
        if not stored_pin:
            logger.warning(f"No PIN found in cache for user {telegram_id}")
            return False
        
        # Проверяем PIN-код
        if stored_pin == pin_code:
            # Удаляем PIN-код после успешного использования (одноразовый)
            await self.cache.delete(key)
            logger.info(f"PIN verified successfully for user {telegram_id}")
            return True
        
        logger.warning(f"PIN mismatch for user {telegram_id}: stored={stored_pin}, provided={pin_code}")
        return False
    
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
