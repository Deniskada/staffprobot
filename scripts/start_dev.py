#!/usr/bin/env python3
"""Скрипт для запуска приложения в режиме разработки."""

import os
import sys
import subprocess
from pathlib import Path

# Добавление корневой директории в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config.settings import settings
from core.logging.logger import logger


def check_environment():
    """Проверка окружения."""
    logger.info("Checking environment...")
    
    # Проверка Python версии
    if sys.version_info < (3, 11):
        logger.error("Python 3.11+ required")
        return False
    
    # Проверка переменных окружения
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        logger.info("Please set TELEGRAM_BOT_TOKEN in .env file")
        return False
    
    logger.info("Environment check passed")
    return True


def install_dependencies():
    """Установка зависимостей."""
    logger.info("Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False


def start_application():
    """Запуск приложения."""
    logger.info("Starting StaffProBot application...")
    
    try:
        # Импорт и запуск приложения
        from main import app
        import uvicorn
        
        uvicorn.run(
            "main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level=settings.log_level.lower()
        )
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return False


def main():
    """Основная функция."""
    logger.info("StaffProBot Development Startup Script")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Проверка окружения
    if not check_environment():
        sys.exit(1)
    
    # Установка зависимостей
    if not install_dependencies():
        sys.exit(1)
    
    # Запуск приложения
    start_application()


if __name__ == "__main__":
    main()







