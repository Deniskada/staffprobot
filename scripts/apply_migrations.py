#!/usr/bin/env python3
"""Скрипт для применения миграций Alembic через Docker."""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config
from core.logging.logger import logger

def apply_migrations():
    """Применяет все доступные миграции."""
    try:
        # Путь к файлу конфигурации Alembic
        alembic_cfg_path = project_root / "alembic.ini"
        
        if not alembic_cfg_path.exists():
            logger.error(f"Alembic config not found at {alembic_cfg_path}")
            return False
        
        # Создаем конфигурацию Alembic
        alembic_cfg = Config(str(alembic_cfg_path))
        
        # Устанавливаем URL базы данных для Docker
        # В Docker используем имена сервисов вместо localhost
        docker_db_url = "postgresql://postgres:password@postgres:5432/staffprobot_dev"
        alembic_cfg.set_main_option("sqlalchemy.url", docker_db_url)
        
        logger.info("Applying Alembic migrations...")
        logger.info(f"Database URL: {docker_db_url}")
        
        # Применяем миграции
        command.upgrade(alembic_cfg, "head")
        
        logger.info("✅ Migrations applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error applying migrations: {e}")
        return False

if __name__ == "__main__":
    success = apply_migrations()
    sys.exit(0 if success else 1)
