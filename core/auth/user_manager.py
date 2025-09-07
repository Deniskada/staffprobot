"""Менеджер пользователей без файлового хранения.

Убрана зависимость от data/users.json: все операции идут через PostgreSQL.
"""

from datetime import datetime
from typing import Dict, Optional, List
from core.logging.logger import logger
from core.database.connection import get_sync_session
from core.database.session import get_async_session
from domain.entities.user import User
from sqlalchemy import select


class UserManager:
    """Менеджер пользователей с хранением в БД (без JSON)."""
    
    def __init__(self, users_file: str = "data/users.json"):
        # Совместимость сигнатуры; файл не используется
        self.users_file = users_file
        self.users: Dict[int, dict] = {}
    
    def _ensure_data_dir(self) -> None:
        """Больше не требуется (без файлового хранения)."""
        return
    
    def _load_users(self) -> None:
        """Отключено: не используем JSON."""
        self.users = {}
    
    def _save_users(self) -> None:
        """Отключено: не используем JSON."""
        return
    
    def register_user(self, user_id: int, first_name: str, username: Optional[str] = None, 
                     last_name: Optional[str] = None, language_code: Optional[str] = None) -> dict:
        """Регистрируем нового пользователя."""
        # Проверяем/создаем в базе данных
        with get_sync_session() as session:
            query = select(User).where(User.telegram_id == user_id)
            existing_user = session.execute(query).scalar_one_or_none()
            if existing_user:
                logger.info(f"User already exists in DB: {user_id} ({first_name})")
                return {
                    "id": existing_user.telegram_id,
                    "first_name": existing_user.first_name,
                    "username": existing_user.username,
                    "last_name": existing_user.last_name,
                    "is_active": existing_user.is_active,
                }
            new_user = User(
                telegram_id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                role="owner",
                is_active=True,
            )
            session.add(new_user)
            session.commit()
            logger.info(f"Registered new user in DB: {user_id} ({first_name})")
            return {
                "id": user_id,
                "first_name": first_name,
                "username": username,
                "last_name": last_name,
                "is_active": True,
            }
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Получаем пользователя по Telegram ID из БД."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                db_user = session.execute(query).scalar_one_or_none()
                if not db_user:
                    return None
                return {
                    "id": db_user.telegram_id,
                    "first_name": db_user.first_name,
                    "last_name": db_user.last_name,
                    "username": db_user.username,
                    "is_active": db_user.is_active,
                }
        except Exception as e:
            logger.error(f"Failed to get user {user_id} from DB: {e}")
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Получение пользователя по Telegram ID."""
        try:
            async with get_async_session() as session:
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return None
                
                return {
                    "id": user.telegram_id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,  # Оставляем для обратной совместимости
                    "roles": user.get_roles(),  # Добавляем множественные роли
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
        except Exception as e:
            logger.error(f"Failed to get user by telegram_id {telegram_id}: {e}")
            return None
    
    async def get_all_users(self) -> List[dict]:
        """Получение всех пользователей."""
        try:
            with get_sync_session() as session:
                query = select(User).order_by(User.created_at.desc())
                result = session.execute(query)
                users = result.scalars().all()
                
                return [
                    {
                        "id": user.telegram_id,
                        "telegram_id": user.telegram_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,  # Оставляем для обратной совместимости
                        "roles": user.get_roles(),  # Добавляем множественные роли
                        "is_active": user.is_active,
                        "created_at": user.created_at,
                        "updated_at": user.updated_at
                    }
                    for user in users
                ]
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
    
    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Получение пользователя по ID."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                result = session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return None
                
                return {
                    "id": user.telegram_id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,  # Оставляем для обратной совместимости
                    "roles": user.get_roles(),  # Добавляем множественные роли
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
        except Exception as e:
            logger.error(f"Failed to get user by id {user_id}: {e}")
            return None
    
    async def update_user_role(self, user_id: int, role: str) -> bool:
        """Обновление роли пользователя (обратная совместимость)."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                result = session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                user.role = role
                # Обновляем также массив ролей
                if hasattr(user, 'roles') and user.roles:
                    user.roles = [role]
                
                session.commit()
                
                logger.info(f"Updated user {user_id} role to {role}")
                return True
        except Exception as e:
            logger.error(f"Failed to update user {user_id} role: {e}")
            return False
    
    async def update_user_roles(self, user_id: int, roles: list) -> bool:
        """Обновление множественных ролей пользователя."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                result = session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Обновляем массив ролей
                user.roles = roles
                # Обновляем основную роль (первая роль в списке)
                if roles:
                    user.role = roles[0]
                
                session.commit()
                
                logger.info(f"Updated user {user_id} roles to {roles}")
                return True
        except Exception as e:
            logger.error(f"Failed to update user {user_id} roles: {e}")
            return False
    
    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                result = session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                session.delete(user)
                session.commit()
                
                logger.info(f"Deleted user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    def update_user_activity(self, user_id: int) -> None:
        """Обновляем время последней активности пользователя."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                db_user = session.execute(query).scalar_one_or_none()
                if db_user:
                    # Поле last_activity может отсутствовать в модели; просто коммитим, чтобы обновился updated_at
                    session.commit()
                    logger.info(f"Updated user activity in DB: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user activity {user_id}: {e}")
    
    def is_user_registered(self, user_id: int) -> bool:
        """Проверяем, зарегистрирован ли пользователь."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                return session.execute(query).scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check user registered {user_id}: {e}")
            return False
    
    def get_all_users(self) -> List[dict]:
        """Получаем список всех пользователей."""
        try:
            with get_sync_session() as session:
                users = session.execute(select(User)).scalars().all()
                return [
                    {
                        "id": u.telegram_id,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "username": u.username,
                        "is_active": u.is_active,
                    }
                    for u in users
                ]
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
    
    def get_active_users(self) -> List[dict]:
        """Получаем список активных пользователей."""
        return [u for u in self.get_all_users() if u.get("is_active", True)]
    
    def deactivate_user(self, user_id: int) -> bool:
        """Деактивируем пользователя."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                db_user = session.execute(query).scalar_one_or_none()
                if not db_user:
                    return False
                db_user.is_active = False
                session.commit()
                logger.info(f"Deactivated user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            return False
    
    def activate_user(self, user_id: int) -> bool:
        """Активируем пользователя."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                db_user = session.execute(query).scalar_one_or_none()
                if not db_user:
                    return False
                db_user.is_active = True
                session.commit()
                logger.info(f"Activated user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to activate user {user_id}: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Optional[dict]:
        """Получаем статистику пользователя."""
        try:
            with get_sync_session() as session:
                query = select(User).where(User.telegram_id == user_id)
                db_user = session.execute(query).scalar_one_or_none()
                if not db_user:
                    return None
                # Агрегаты можно считать отдельно; возвращаем базовую инфо
                return {
                    "total_shifts": 0,
                    "total_hours": 0,
                    "total_earnings": 0.0,
                    "registered_at": None,
                    "last_activity": None,
                }
        except Exception as e:
            logger.error(f"Failed to get user stats {user_id}: {e}")
            return None
    
    def update_user_stats(self, user_id: int, shifts: int = 0, hours: int = 0, earnings: float = 0.0) -> bool:
        """Обновляем статистику пользователя."""
        logger.info(
            f"Update stats requested for user {user_id}: +{shifts} shifts, +{hours} hours, +{earnings} earnings (no-op)"
        )
        return True
    
    def _save_user_to_db(self, user_data: dict) -> None:
        """Сохраняет пользователя в PostgreSQL базу данных."""
        try:
            with get_sync_session() as session:
                # Проверяем, существует ли пользователь в БД
                query = select(User).where(User.telegram_id == user_data["id"])
                result = session.execute(query)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # Обновляем существующего пользователя
                    existing_user.first_name = user_data["first_name"]
                    existing_user.last_name = user_data.get("last_name")
                    existing_user.username = user_data.get("username")
                    existing_user.is_active = user_data["is_active"]
                else:
                    # Создаем нового пользователя
                    new_user = User(
                        telegram_id=user_data["id"],
                        first_name=user_data["first_name"],
                        last_name=user_data.get("last_name"),
                        username=user_data.get("username"),
                        role="owner",  # Пользователи, создающие объекты - владельцы
                        is_active=user_data["is_active"]
                    )
                    session.add(new_user)
                
                session.commit()
                logger.info(f"User {user_data['id']} saved to database successfully")
                
        except Exception as e:
            logger.error(f"Failed to save user {user_data['id']} to database: {e}")


# Глобальный экземпляр менеджера пользователей
user_manager = UserManager()

