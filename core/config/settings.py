"""Настройки приложения StaffProBot."""

from pydantic import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Основные настройки приложения."""
    
    # Основные настройки
    app_name: str = "StaffProBot"
    debug: bool = False
    environment: str = "development"
    version: str = "0.1.0"
    
    # База данных
    database_url: str = "postgresql://postgres:password@localhost:5432/staffprobot"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    database_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # User State Backend
    state_backend: str = "redis"  # memory | redis
    state_ttl_minutes: int = 15
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://admin:password@localhost:5672"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 500
    openai_temperature: float = 0.7
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_path: str = "/webhook"
    
    # Email (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: str = "StaffProBot"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout: int = 30
    
    # Геолокация
    max_distance_meters: int = 500  # Увеличено для тестирования в регионах с неточной геолокацией
    location_accuracy_meters: int = 200  # Увеличено для реальных условий GPS (было 50м)
    
    # UX ограничения
    max_active_shifts_per_user: int = 1
    require_location_for_shifts: bool = True
    location_timeout_seconds: int = 300  # 5 минут на отправку геопозиции
    
    # Временные зоны
    default_timezone: str = "Europe/Moscow"  # Часовой пояс по умолчанию
    
    # Мониторинг
    prometheus_port: int = 9090
    grafana_port: int = 3000
    
    # Безопасность
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 часа
    
    # Системные настройки
    domain: str = "localhost:8001"
    ssl_email: str = "admin@localhost"
    nginx_config_path: str = "/etc/nginx/sites-available"
    certbot_path: str = "/usr/bin/certbot"
    use_https: bool = False
    
    # Логирование
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    class Config:
        # В production читаем .env.prod, иначе .env
        env_file = ".env.prod" if os.getenv("ENVIRONMENT") == "production" else ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Создание экземпляра настроек
settings = Settings()


def validate_settings() -> None:
    """Валидация обязательных настроек."""
    required_vars = [
        'telegram_bot_token',
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")


# Валидация при импорте (только для production)
if settings.environment == "production":
    validate_settings()

