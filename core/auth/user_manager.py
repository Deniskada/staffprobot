"""Простой менеджер пользователей для MVP без базы данных."""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List
from core.logging.logger import logger
from core.database.connection import get_sync_session
from domain.entities.user import User
from sqlalchemy import select


class UserManager:
    """Менеджер пользователей с JSON хранением."""
    
    def __init__(self, users_file: str = "data/users.json"):
        self.users_file = users_file
        self.users: Dict[int, dict] = {}
        self._ensure_data_dir()
        self._load_users()
    
    def _ensure_data_dir(self) -> None:
        """Создаем папку для данных, если её нет."""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
    
    def _load_users(self) -> None:
        """Загружаем пользователей из JSON файла."""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем ключи обратно в int (JSON сохраняет их как строки)
                    self.users = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
            else:
                logger.info(f"Users file {self.users_file} not found, starting with empty users")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            self.users = {}
    
    def _save_users(self) -> None:
        """Сохраняем пользователей в JSON файл."""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Failed to save users: {e}")
    
    def register_user(self, user_id: int, first_name: str, username: Optional[str] = None, 
                     last_name: Optional[str] = None, language_code: Optional[str] = None) -> dict:
        """Регистрируем нового пользователя."""
        # Проверяем, существует ли уже пользователь
        if user_id in self.users:
            # Обновляем только активность существующего пользователя
            self.users[user_id]["last_activity"] = datetime.now().isoformat()
            self._save_users()
            logger.info(f"Updated activity for existing user: {user_id} ({first_name})")
            return self.users[user_id]
        
        # Создаем нового пользователя
        now = datetime.now().isoformat()
        
        user_data = {
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "last_name": last_name,
            "language_code": language_code,
            "registered_at": now,
            "last_activity": now,
            "is_active": True,
            "total_shifts": 0,
            "total_hours": 0,
            "total_earnings": 0.0
        }
        
        self.users[user_id] = user_data
        self._save_users()
        
        # Сохраняем в базу данных PostgreSQL
        self._save_user_to_db(user_data)
        
        logger.info(f"Registered new user: {user_id} ({first_name})")
        return user_data
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Получаем пользователя по ID."""
        return self.users.get(user_id)
    
    def update_user_activity(self, user_id: int) -> None:
        """Обновляем время последней активности пользователя."""
        if user_id in self.users:
            self.users[user_id]["last_activity"] = datetime.now().isoformat()
            self._save_users()
            # Обновляем в БД
            self._save_user_to_db(self.users[user_id])
    
    def is_user_registered(self, user_id: int) -> bool:
        """Проверяем, зарегистрирован ли пользователь."""
        return user_id in self.users
    
    def get_all_users(self) -> List[dict]:
        """Получаем список всех пользователей."""
        return list(self.users.values())
    
    def get_active_users(self) -> List[dict]:
        """Получаем список активных пользователей."""
        return [user for user in self.users.values() if user.get("is_active", True)]
    
    def deactivate_user(self, user_id: int) -> bool:
        """Деактивируем пользователя."""
        if user_id in self.users:
            self.users[user_id]["is_active"] = False
            self._save_users()
            logger.info(f"Deactivated user: {user_id}")
            return True
        return False
    
    def activate_user(self, user_id: int) -> bool:
        """Активируем пользователя."""
        if user_id in self.users:
            self.users[user_id]["is_active"] = True
            self._save_users()
            logger.info(f"Activated user: {user_id}")
            return True
        return False
    
    def get_user_stats(self, user_id: int) -> Optional[dict]:
        """Получаем статистику пользователя."""
        user = self.get_user(user_id)
        if not user:
            return None
        
        return {
            "total_shifts": user.get("total_shifts", 0),
            "total_hours": user.get("total_hours", 0),
            "total_earnings": user.get("total_earnings", 0.0),
            "registered_at": user.get("registered_at"),
            "last_activity": user.get("last_activity")
        }
    
    def update_user_stats(self, user_id: int, shifts: int = 0, hours: int = 0, earnings: float = 0.0) -> bool:
        """Обновляем статистику пользователя."""
        if user_id in self.users:
            self.users[user_id]["total_shifts"] += shifts
            self.users[user_id]["total_hours"] += hours
            self.users[user_id]["total_earnings"] += earnings
            self._save_users()
            logger.info(f"Updated stats for user {user_id}: +{shifts} shifts, +{hours} hours, +{earnings} earnings")
            return True
        return False
    
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

