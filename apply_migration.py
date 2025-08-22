#!/usr/bin/env python3
"""
Скрипт для применения миграции Alembic
"""

import sys
import os

def main():
    """Применяет миграцию Alembic"""
    try:
        # Добавляем текущую директорию в путь
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Импортируем Alembic
        from alembic import command
        from alembic.config import Config
        
        # Создаем конфигурацию
        alembic_cfg = Config("alembic.ini")
        
        print("Применяем миграцию...")
        command.upgrade(alembic_cfg, "head")
        print("Миграция применена успешно!")
        
    except Exception as e:
        print(f"Ошибка при применении миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
