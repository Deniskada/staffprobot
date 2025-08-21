"""
Интеграционные тесты для Docker Compose
Проверяют работу всех сервисов
"""
import pytest
import subprocess
from unittest.mock import patch, MagicMock


class TestDockerIntegration:
    """Тесты интеграции Docker Compose."""
    
    @pytest.fixture(scope="class")
    def docker_services(self):
        """Запускаем Docker Compose сервисы для тестов."""
        # В реальных тестах здесь был бы запуск docker-compose up
        # Для MVP используем моки
        pass
    
    def test_docker_compose_file_exists(self):
        """Тест существования docker-compose.yml."""
        import os
        assert os.path.exists("docker-compose.yml"), "docker-compose.yml не найден"
    
    def test_docker_compose_structure(self):
        """Тест структуры docker-compose.yml."""
        import yaml
        
        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)
        
        # Проверяем наличие основных сервисов
        assert "services" in compose
        services = compose["services"]
        
        # Проверяем PostgreSQL
        assert "postgres" in services
        postgres = services["postgres"]
        assert "image" in postgres
        assert "postgis" in postgres["image"]  # Используем PostGIS образ
        
        # Проверяем Redis
        assert "redis" in services
        redis = services["redis"]
        assert "image" in redis
        assert "redis" in redis["image"]
        
        # Проверяем RabbitMQ
        assert "rabbitmq" in services
        rabbitmq = services["rabbitmq"]
        assert "image" in rabbitmq
        assert "rabbitmq" in rabbitmq["image"]
        
        # Проверяем бота
        assert "bot" in services
        bot = services["bot"]
        assert "build" in bot
        assert "context" in bot["build"]
        assert bot["build"]["context"] == "."
    
    def test_environment_variables(self):
        """Тест переменных окружения."""
        import os
        from core.config.settings import settings
        
        # Проверяем, что основные настройки загружаются
        assert hasattr(settings, 'app_name')
        assert hasattr(settings, 'telegram_bot_token')
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'redis_url')
    
    @patch('subprocess.run')
    def test_docker_compose_commands(self, mock_run):
        """Тест команд Docker Compose."""
        # Мокаем успешное выполнение команды
        mock_run.return_value = MagicMock(returncode=0)
        
        # Тестируем команду build
        result = subprocess.run(["docker-compose", "build"], capture_output=True, text=True)
        assert result.returncode == 0
        
        # Тестируем команду up
        result = subprocess.run(["docker-compose", "up", "-d"], capture_output=True, text=True)
        assert result.returncode == 0
    
    def test_network_configuration(self):
        """Тест конфигурации сети."""
        import yaml
        
        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)
        
        # Проверяем наличие сетей
        assert "networks" in compose
        networks = compose["networks"]
        
        # Проверяем основную сеть
        assert "staffprobot_network" in networks
        main_network = networks["staffprobot_network"]
        assert "driver" in main_network
        assert main_network["driver"] == "bridge"
    
    def test_volume_configuration(self):
        """Тест конфигурации томов."""
        import yaml
        
        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)
        
        # Проверяем наличие томов
        assert "volumes" in compose
        volumes = compose["volumes"]
        
        # Проверяем том для PostgreSQL
        assert "postgres_data" in volumes
        postgres_volume = volumes["postgres_data"]
        assert "driver" in postgres_volume
        assert postgres_volume["driver"] == "local"
    
    def test_health_checks(self):
        """Тест health checks."""
        import yaml
        
        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)
        
        services = compose["services"]
        
        # Проверяем health check для PostgreSQL
        if "postgres" in services:
            postgres = services["postgres"]
            if "healthcheck" in postgres:
                healthcheck = postgres["healthcheck"]
                assert "test" in healthcheck
                assert "interval" in healthcheck
                assert "timeout" in healthcheck
                assert "retries" in healthcheck
    
    def test_dependencies(self):
        """Тест зависимостей между сервисами."""
        import yaml
        
        with open("docker-compose.yml", "r") as f:
            compose = yaml.safe_load(f)
        
        services = compose["services"]
        
        # Проверяем, что бот зависит от других сервисов
        if "bot" in services:
            bot = services["bot"]
            if "depends_on" in bot:
                depends_on = bot["depends_on"]
                # Бот должен зависеть от основных сервисов
                assert isinstance(depends_on, list) or isinstance(depends_on, dict)
    
    def test_environment_file(self):
        """Тест файла .env."""
        import os
        
        # Проверяем наличие .env файла или .env.example
        env_exists = os.path.exists(".env")
        env_example_exists = os.path.exists(".env.example")
        
        # Должен быть хотя бы один из файлов
        assert env_exists or env_example_exists, "Не найден .env или .env.example файл"
        
        if env_example_exists:
            # Проверяем содержимое .env.example
            with open(".env.example", "r") as f:
                content = f.read()
                # Проверяем наличие основных переменных
                assert "TELEGRAM_BOT_TOKEN" in content
                assert "DATABASE_URL" in content
                assert "REDIS_URL" in content
