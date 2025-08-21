"""
Конфигурация pytest для интеграционных тестов
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Создаем временную директорию для тестовых данных."""
    temp_dir = tempfile.mkdtemp(prefix="staffprobot_test_")
    yield temp_dir
    # Очищаем после тестов
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="session")
def test_env_file(test_data_dir):
    """Создаем временный .env файл для тестов."""
    env_file = os.path.join(test_data_dir, ".env")
    
    env_content = """
# Тестовые переменные окружения
APP_NAME=StaffProBot Test
TELEGRAM_BOT_TOKEN=test_token_12345
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
OPENAI_API_KEY=test_key_12345
LOG_LEVEL=DEBUG
"""
    
    with open(env_file, "w") as f:
        f.write(env_content)
    
    return env_file


@pytest.fixture(scope="session")
def test_user_data_file(test_data_dir):
    """Создаем временный файл с тестовыми данными пользователей."""
    user_data_file = os.path.join(test_data_dir, "users.json")
    
    user_data = {
        "12345": {
            "id": 12345,
            "first_name": "Test",
            "username": "test_user",
            "last_name": "User",
            "language_code": "ru",
            "is_active": True,
            "registered_at": "2025-01-01T00:00:00",
            "last_activity": "2025-01-01T00:00:00",
            "total_shifts": 5,
            "total_hours": 40,
            "total_earnings": 1000.0
        }
    }
    
    import json
    with open(user_data_file, "w") as f:
        json.dump(user_data, f, indent=2)
    
    return user_data_file


@pytest.fixture(autouse=True)
def setup_test_environment(test_env_file, test_user_data_file, monkeypatch):
    """Настраиваем тестовое окружение."""
    # Устанавливаем переменные окружения для тестов
    monkeypatch.setenv("STAFFPROBOT_DATA_DIR", os.path.dirname(test_user_data_file))
    
    # Не мокаем атрибуты UserManager - они устанавливаются в конструкторе
    # Каждый тест создает свой экземпляр с нужным путем


@pytest.fixture(scope="function")
def clean_user_data(test_user_data_file):
    """Очищаем данные пользователей перед каждым тестом."""
    from core.auth.user_manager import UserManager
    # Создаем новый экземпляр для каждого теста с тестовым файлом
    user_manager = UserManager(users_file=test_user_data_file)
    user_manager.users.clear()
    user_manager._save_users()
    yield user_manager
    # Очищаем после теста
    user_manager.users.clear()
    user_manager._save_users()
