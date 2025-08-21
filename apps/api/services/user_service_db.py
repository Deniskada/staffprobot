"""
Сервис для работы с пользователями через базу данных
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.user import User

logger = logging.getLogger(__name__)


class UserServiceDB:
    """Сервис для работы с пользователями в базе данных."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        """Создает нового пользователя."""
        try:
            # Проверяем уникальность telegram_id
            existing_user = await self.get_user_by_telegram_id(user_data['telegram_id'])
            if existing_user:
                logger.error(f"User with telegram_id {user_data['telegram_id']} already exists")
                return None
            
            # Создаем пользователя
            new_user = User(**user_data)
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            
            logger.info(f"User created successfully: {new_user.id}")
            return new_user
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while creating user: {e}")
            await self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error while creating user: {e}")
            await self.db.rollback()
            return None
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получает пользователя по ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting user {user_id}: {e}")
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя по Telegram ID."""
        try:
            query = select(User).where(User.telegram_id == telegram_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting user by telegram_id {telegram_id}: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получает пользователя по username."""
        try:
            query = select(User).where(User.username == username)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting user by username {username}: {e}")
            return None
    
    async def get_all_users(self) -> List[User]:
        """Получает всех активных пользователей."""
        try:
            query = select(User).where(User.is_active == True)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting all users: {e}")
            return []
    
    async def get_users_by_role(self, role: str) -> List[User]:
        """Получает пользователей по роли."""
        try:
            query = select(User).where(User.role == role, User.is_active == True)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while getting users by role {role}: {e}")
            return []
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Обновляет пользователя."""
        try:
            query = update(User).where(User.id == user_id).values(**update_data)
            result = await self.db.execute(query)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"User {user_id} updated successfully")
                return True
            else:
                logger.warning(f"User {user_id} not found for update")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Database error while updating user {user_id}: {e}")
            await self.db.rollback()
            return False
    
    async def deactivate_user(self, user_id: int) -> bool:
        """Деактивирует пользователя."""
        try:
            query = update(User).where(User.id == user_id).values(is_active=False)
            result = await self.db.execute(query)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"User {user_id} deactivated successfully")
                return True
            else:
                logger.warning(f"User {user_id} not found for deactivation")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Database error while deactivating user {user_id}: {e}")
            await self.db.rollback()
            return False
    
    async def search_users(self, search_term: str) -> List[User]:
        """Ищет пользователей по имени, фамилии или username."""
        try:
            query = select(User).where(
                User.is_active == True,
                (User.first_name.ilike(f"%{search_term}%") | 
                 User.last_name.ilike(f"%{search_term}%") | 
                 User.username.ilike(f"%{search_term}%"))
            )
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while searching users: {e}")
            return []
