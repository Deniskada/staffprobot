"""Unit тесты для UserManager."""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open
from core.auth.user_manager import UserManager


class TestUserManager:
    """Тесты для UserManager."""
    
    @pytest.fixture
    def temp_users_file(self):
        """Временный файл для тестов."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{}')
            temp_file = f.name
        
        yield temp_file
        
        # Очищаем после тестов
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def user_manager(self, temp_users_file):
        """Экземпляр UserManager для тестов."""
        return UserManager(users_file=temp_users_file)
    
    @pytest.fixture
    def sample_user_data(self):
        """Тестовые данные пользователя."""
        return {
            "user_id": 12345,
            "first_name": "Test",
            "username": "testuser",
            "last_name": "User",
            "language_code": "ru"
        }
    
    def test_init_creates_data_dir(self, temp_users_file):
        """Тест создания папки для данных."""
        # Удаляем файл, чтобы проверить создание папки
        os.unlink(temp_users_file)
        dir_path = os.path.dirname(temp_users_file)
        
        # Создаем UserManager - должен создать папку
        user_manager = UserManager(users_file=temp_users_file)
        
        assert os.path.exists(dir_path)
    
    def test_load_users_empty_file(self, user_manager):
        """Тест загрузки пустого файла пользователей."""
        assert len(user_manager.users) == 0
    
    def test_load_users_with_data(self, temp_users_file):
        """Тест загрузки файла с данными пользователей."""
        # Создаем тестовые данные
        test_data = {
            "12345": {
                "id": 12345,
                "first_name": "Test",
                "username": "testuser",
                "registered_at": "2025-08-19T16:00:00"
            }
        }
        
        with open(temp_users_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        user_manager = UserManager(users_file=temp_users_file)
        
        assert len(user_manager.users) == 1
        assert 12345 in user_manager.users
        assert user_manager.users[12345]["first_name"] == "Test"
    
    def test_register_user_new(self, user_manager, sample_user_data):
        """Тест регистрации нового пользователя."""
        user_data = user_manager.register_user(**sample_user_data)
        
        assert user_data["id"] == 12345
        assert user_data["first_name"] == "Test"
        assert user_data["username"] == "testuser"
        assert user_data["total_shifts"] == 0
        assert user_data["total_hours"] == 0
        assert user_data["total_earnings"] == 0.0
        assert "registered_at" in user_data
        assert "last_activity" in user_data
        assert user_data["is_active"] is True
        
        # Проверяем, что пользователь сохранен в памяти
        assert 12345 in user_manager.users
    
    def test_register_user_existing(self, user_manager, sample_user_data):
        """Тест повторной регистрации пользователя."""
        # Регистрируем первый раз
        first_user_data = user_manager.register_user(**sample_user_data)
        first_registration = first_user_data["registered_at"]
        
        # Регистрируем второй раз
        second_user_data = user_manager.register_user(**sample_user_data)
        
        # Проверяем, что время регистрации осталось первым
        assert second_user_data["registered_at"] == first_registration
        assert second_user_data["id"] == 12345
        
        # Проверяем, что в словаре пользователей только один пользователь
        assert len(user_manager.users) == 1
        assert 12345 in user_manager.users
    
    def test_get_user_existing(self, user_manager, sample_user_data):
        """Тест получения существующего пользователя."""
        user_manager.register_user(**sample_user_data)
        
        user = user_manager.get_user(12345)
        
        assert user is not None
        assert user["id"] == 12345
        assert user["first_name"] == "Test"
    
    def test_get_user_nonexistent(self, user_manager):
        """Тест получения несуществующего пользователя."""
        user = user_manager.get_user(99999)
        
        assert user is None
    
    def test_is_user_registered_true(self, user_manager, sample_user_data):
        """Тест проверки зарегистрированного пользователя."""
        user_manager.register_user(**sample_user_data)
        
        assert user_manager.is_user_registered(12345) is True
    
    def test_is_user_registered_false(self, user_manager):
        """Тест проверки незарегистрированного пользователя."""
        assert user_manager.is_user_registered(99999) is False
    
    def test_update_user_activity(self, user_manager, sample_user_data):
        """Тест обновления активности пользователя."""
        user_manager.register_user(**sample_user_data)
        
        # Получаем время до обновления
        before_update = user_manager.users[12345]["last_activity"]
        
        # Обновляем активность
        user_manager.update_user_activity(12345)
        
        # Проверяем, что время изменилось
        after_update = user_manager.users[12345]["last_activity"]
        assert after_update != before_update
    
    def test_get_user_stats_existing(self, user_manager, sample_user_data):
        """Тест получения статистики существующего пользователя."""
        user_manager.register_user(**sample_user_data)
        
        stats = user_manager.get_user_stats(12345)
        
        assert stats is not None
        assert stats["total_shifts"] == 0
        assert stats["total_hours"] == 0
        assert stats["total_earnings"] == 0.0
        assert "registered_at" in stats
        assert "last_activity" in stats
    
    def test_get_user_stats_nonexistent(self, user_manager):
        """Тест получения статистики несуществующего пользователя."""
        stats = user_manager.get_user_stats(99999)
        
        assert stats is None
    
    def test_update_user_stats(self, user_manager, sample_user_data):
        """Тест обновления статистики пользователя."""
        user_manager.register_user(**sample_user_data)
        
        # Обновляем статистику
        success = user_manager.update_user_stats(12345, shifts=2, hours=16, earnings=1000.0)
        
        assert success is True
        
        # Проверяем, что статистика обновилась
        stats = user_manager.get_user_stats(12345)
        assert stats["total_shifts"] == 2
        assert stats["total_hours"] == 16
        assert stats["total_earnings"] == 1000.0
    
    def test_update_user_stats_nonexistent(self, user_manager):
        """Тест обновления статистики несуществующего пользователя."""
        success = user_manager.update_user_stats(99999, shifts=1, hours=8, earnings=500.0)
        
        assert success is False
    
    def test_get_all_users(self, user_manager, sample_user_data):
        """Тест получения всех пользователей."""
        user_manager.register_user(**sample_user_data)
        
        all_users = user_manager.get_all_users()
        
        assert len(all_users) == 1
        assert all_users[0]["id"] == 12345
    
    def test_get_active_users(self, user_manager, sample_user_data):
        """Тест получения активных пользователей."""
        user_manager.register_user(**sample_user_data)
        
        active_users = user_manager.get_active_users()
        
        assert len(active_users) == 1
        assert active_users[0]["id"] == 12345
        assert active_users[0]["is_active"] is True
    
    def test_deactivate_user(self, user_manager, sample_user_data):
        """Тест деактивации пользователя."""
        user_manager.register_user(**sample_user_data)
        
        # Деактивируем пользователя
        success = user_manager.deactivate_user(12345)
        
        assert success is True
        assert user_manager.users[12345]["is_active"] is False
    
    def test_activate_user(self, user_manager, sample_user_data):
        """Тест активации пользователя."""
        user_manager.register_user(**sample_user_data)
        user_manager.deactivate_user(12345)  # Сначала деактивируем
        
        # Активируем пользователя
        success = user_manager.activate_user(12345)
        
        assert success is True
        assert user_manager.users[12345]["is_active"] is True
    
    def test_save_users_error_handling(self, user_manager, sample_user_data):
        """Тест обработки ошибок при сохранении."""
        user_manager.register_user(**sample_user_data)
        
        # Мокаем ошибку при сохранении
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            # Должно обработать ошибку без падения
            user_manager._save_users()
    
    def test_load_users_error_handling(self, temp_users_file):
        """Тест обработки ошибок при загрузке."""
        # Создаем файл с некорректным JSON
        with open(temp_users_file, 'w') as f:
            f.write('{"invalid": json}')
        
        # Должно обработать ошибку и создать пустой словарь
        user_manager = UserManager(users_file=temp_users_file)
        
        assert len(user_manager.users) == 0

