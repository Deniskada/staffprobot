#!/usr/bin/env python3
"""
Скрипт для создания миграции Alembic
"""

import subprocess
import sys
import os

def main():
    """Создает миграцию Alembic"""
    try:
        # Добавляем текущую директорию в путь
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Импортируем Alembic
        from alembic import command
        from alembic.config import Config
        
        # Создаем конфигурацию
        alembic_cfg = Config("alembic.ini")
        
        # Получаем сообщение миграции из аргументов командной строки
        if len(sys.argv) > 1:
            message = sys.argv[1]
        else:
            message = input("Введите описание миграции: ")
        
        print(f"Создаем миграцию: {message}")
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message=message
        )
        print("Миграция создана успешно!")
        
    except Exception as e:
        print(f"Ошибка при создании миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
