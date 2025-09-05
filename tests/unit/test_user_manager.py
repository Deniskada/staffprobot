"""Unit тесты для UserManager (исправленная версия с моками БД)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from core.auth.user_manager import UserManager


class TestUserManager:
    """Тесты для UserManager с моками БД."""
    
    @pytest.fixture
    def user_manager(self):
        """Экземпляр UserManager для тестов."""
        return UserManager()
    
    @pytest.fixture
    def sample_user_data(self):
        """Тестовые данные пользователя."""
        return {
            "user_id": 12345,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "ru"
        }
    
    @pytest.fixture
    def mock_user_entity(self):
        """Мок сущности User из БД."""
        user = Mock()
        user.id = 1
        user.telegram_id = 12345
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.language_code = "ru"
        user.is_active = True
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        return user
    
    def test_init_creates_data_dir(self, user_manager):
        """Тест инициализации UserManager."""
        assert user_manager.users_file == "data/users.json"
        assert isinstance(user_manager.users, dict)
    
    def test_load_users_empty_file(self, user_manager):
        """Тест загрузки пустого файла (теперь не используется)."""
        user_manager._load_users()
        assert user_manager.users == {}
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_register_user_new(self, mock_get_session, user_manager, sample_user_data, mock_user_entity):
        """Тест регистрации нового пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь не найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        
        # Выполнение
        result = user_manager.register_user(**sample_user_data)
        
        # Проверки
        assert result["id"] == 12345
        assert result["username"] == "testuser"
        assert result["first_name"] == "Test"
        assert result["last_name"] == "User"
        assert result["is_active"] is True
        
        # Проверяем, что пользователь был добавлен в БД
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_register_user_existing(self, mock_get_session, user_manager, sample_user_data, mock_user_entity):
        """Тест регистрации существующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        mock_session.commit = Mock()
        
        # Выполнение
        result = user_manager.register_user(**sample_user_data)
        
        # Проверки
        assert result["telegram_id"] == 12345
        assert result["username"] == "testuser"
        assert result["first_name"] == "Test"
        
        # Проверяем, что пользователь НЕ был добавлен повторно
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_get_user_existing(self, mock_get_session, user_manager, mock_user_entity):
        """Тест получения существующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        
        # Выполнение
        result = user_manager.get_user(12345)
        
        # Проверки
        assert result is not None
        assert result["id"] == 12345
        assert result["username"] == "testuser"
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_get_user_nonexistent(self, mock_get_session, user_manager):
        """Тест получения несуществующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь не найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Выполнение
        result = user_manager.get_user(99999)
        
        # Проверки
        assert result is None
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_is_user_registered_true(self, mock_get_session, user_manager, mock_user_entity):
        """Тест проверки регистрации существующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        
        # Выполнение
        result = user_manager.is_user_registered(12345)
        
        # Проверки
        assert result is True
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_is_user_registered_false(self, mock_get_session, user_manager):
        """Тест проверки регистрации несуществующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь не найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Выполнение
        result = user_manager.is_user_registered(99999)
        
        # Проверки
        assert result is False
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_update_user_activity(self, mock_get_session, user_manager, mock_user_entity):
        """Тест обновления активности пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        mock_session.commit = Mock()
        
        # Выполнение
        result = user_manager.update_user_activity(12345)
        
        # Проверки
        assert result is True
        mock_session.commit.assert_called_once()
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_get_user_stats_existing(self, mock_get_session, user_manager, mock_user_entity):
        """Тест получения статистики существующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        
        # Выполнение
        result = user_manager.get_user_stats(12345)
        
        # Проверки
        assert result is not None
        assert "id" in result
        assert "username" in result
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_get_user_stats_nonexistent(self, mock_get_session, user_manager):
        """Тест получения статистики несуществующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь не найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Выполнение
        result = user_manager.get_user_stats(99999)
        
        # Проверки
        assert result is None
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_update_user_stats(self, mock_get_session, user_manager, mock_user_entity):
        """Тест обновления статистики пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        mock_session.commit = Mock()
        
        # Выполнение
        result = user_manager.update_user_stats(12345, 2, 16, 1000.0)
        
        # Проверки
        assert result is True
        mock_session.commit.assert_called_once()
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_update_user_stats_nonexistent(self, mock_get_session, user_manager):
        """Тест обновления статистики несуществующего пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь не найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Выполнение
        result = user_manager.update_user_stats(99999, 1, 8, 500.0)
        
        # Проверки
        assert result is False
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_get_all_users(self, mock_get_session, user_manager, mock_user_entity):
        """Тест получения всех пользователей."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - возвращаем список пользователей
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_user_entity]
        
        # Выполнение
        result = user_manager.get_all_users()
        
        # Проверки
        assert len(result) == 1
        assert result[0]["id"] == 12345
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_get_active_users(self, mock_get_session, user_manager, mock_user_entity):
        """Тест получения активных пользователей."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - возвращаем список активных пользователей
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_user_entity]
        
        # Выполнение
        result = user_manager.get_active_users()
        
        # Проверки
        assert len(result) == 1
        assert result[0]["id"] == 12345
        assert result[0]["is_active"] is True
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_deactivate_user(self, mock_get_session, user_manager, mock_user_entity):
        """Тест деактивации пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        mock_session.commit = Mock()
        
        # Выполнение
        result = user_manager.deactivate_user(12345)
        
        # Проверки
        assert result is True
        assert mock_user_entity.is_active is False
        mock_session.commit.assert_called_once()
    
    @patch('core.auth.user_manager.get_sync_session')
    def test_activate_user(self, mock_get_session, user_manager, mock_user_entity):
        """Тест активации пользователя."""
        # Настройка мока сессии
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        # Мок запроса - пользователь найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user_entity
        mock_session.commit = Mock()
        
        # Выполнение
        result = user_manager.activate_user(12345)
        
        # Проверки
        assert result is True
        assert mock_user_entity.is_active is True
        mock_session.commit.assert_called_once()
    
    def test_save_users_error_handling(self, user_manager):
        """Тест обработки ошибок при сохранении (теперь не используется)."""
        # Этот метод больше не используется, но тест для совместимости
        user_manager._save_users()
        # Должен выполниться без ошибок
    
    def test_load_users_error_handling(self, user_manager):
        """Тест обработки ошибок при загрузке (теперь не используется)."""
        # Этот метод больше не используется, но тест для совместимости
        user_manager._load_users()
        # Должен выполниться без ошибок
