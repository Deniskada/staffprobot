#!/usr/bin/env python3
"""Скрипт для применения миграций в Docker окружении."""

import os
import sys
from alembic import command
from alembic.config import Config

def apply_migrations():
    """Применяет миграции к базе данных."""
    
    # URL для Docker окружения
    database_url = "postgresql://postgres:password@postgres:5432/staffprobot_dev"
    
    # Создаем конфигурацию Alembic
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    print(f"Применяем миграции к базе данных: {database_url}")
    
    try:
        # Применяем все миграции
        command.upgrade(alembic_cfg, "head")
        print("✅ Миграции успешно применены!")
        
        # Показываем текущую версию
        command.current(alembic_cfg)
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграций: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migrations()
