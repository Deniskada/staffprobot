"""Сервис для работы с пользователями."""

from typing import Optional, Dict, Any
from datetime import datetime
from core.logging.logger import logger
from core.database.connection import get_async_session, get_sync_session
from domain.entities.user import User


class UserService:
    """Сервис для работы с пользователями."""
    
    async def ensure_user_registered(self, telegram_user) -> User:
        """Обеспечение регистрации пользователя."""
        try:
            async with get_async_session() as session:
                # Поиск существующего пользователя
                existing_user = await self._find_user_by_telegram_id(
                    session, telegram_user.id
                )
                
                if existing_user:
                    logger.info(
                        "User already registered",
                        user_id=existing_user.id,
                        telegram_id=telegram_user.id
                    )
                    return existing_user
                
                # Создание нового пользователя
                new_user = await self._create_user(session, telegram_user)
                
                logger.info(
                    "New user registered",
                    user_id=new_user.id,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username
                )
                
                return new_user
                
        except Exception as e:
            logger.error(
                f"Failed to ensure user registration: {e}",
                telegram_id=telegram_user.id
            )
            raise
    
    async def get_user_status(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение статуса пользователя."""
        try:
            async with get_async_session() as session:
                user = await self._find_user_by_telegram_id(session, telegram_id)
                
                if not user:
                    return None
                
                # Получение статистики смен
                active_shifts = await self._count_active_shifts(session, user.id)
                completed_shifts = await self._count_completed_shifts(session, user.id)
                total_earnings = await self._calculate_total_earnings(session, user.id)
                
                return {
                    'full_name': user.full_name,
                    'role': user.role,
                    'created_at': user.created_at.strftime('%d.%m.%Y'),
                    'active_shifts': active_shifts,
                    'completed_shifts': completed_shifts,
                    'total_earnings': total_earnings
                }
                
        except Exception as e:
            logger.error(
                f"Failed to get user status: {e}",
                telegram_id=telegram_id
            )
            raise
    
    async def _find_user_by_telegram_id(self, session, telegram_id: int) -> Optional[User]:
        """Поиск пользователя по Telegram ID."""
        # Заглушка для MVP - в реальной реализации здесь будет SQL запрос
        return None
    
    async def _create_user(self, session, telegram_user) -> User:
        """Создание нового пользователя."""
        # Заглушка для MVP - в реальной реализации здесь будет SQL запрос
        user = User(
            id=1,  # Временный ID
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            role="employee",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        return user
    
    async def _count_active_shifts(self, session, user_id: int) -> int:
        """Подсчет активных смен пользователя."""
        # Заглушка для MVP
        return 0
    
    async def _count_completed_shifts(self, session, user_id: int) -> int:
        """Подсчет завершенных смен пользователя."""
        # Заглушка для MVP
        return 0
    
    async def _calculate_total_earnings(self, session, user_id: int) -> float:
        """Расчет общего заработка пользователя."""
        # Заглушка для MVP
        return 0.0
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Синхронное получение пользователя по Telegram ID."""
        try:
            logger.info(f"Searching for user with telegram_id: {telegram_id}")
            db = get_sync_session()
            try:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                
                if not user:
                    logger.warning(f"User not found for telegram_id: {telegram_id}")
                    return None
                
                logger.info(f"Found user: ID={user.id}, telegram_id={user.telegram_id}")
                
                return {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_active': user.is_active
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to get user by telegram_id: {e}")
            return None







