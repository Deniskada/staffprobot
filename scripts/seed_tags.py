#!/usr/bin/env python3
"""
Скрипт для инициализации справочника тегов.
"""

import asyncio
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.session import get_async_session
from apps.web.services.tag_service import TagService


async def seed_tags():
    """Заполнение справочника тегов."""
    
    try:
        async with get_async_session() as session:
            tag_service = TagService()
            await tag_service.create_default_tags(session)
            print("✅ Справочник тегов успешно создан")
            
    except Exception as e:
        print(f"❌ Ошибка инициализации справочника тегов: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed_tags())
