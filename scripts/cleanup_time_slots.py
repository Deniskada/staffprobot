#!/usr/bin/env python3
"""
Скрипт для очистки тайм-слотов без ID (NULL id) из базы данных.
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_time_slots():
    """Очистка тайм-слотов без ID."""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL не установлен")
        return False
    
    # Создаем асинхронный движок
    engine = create_async_engine(database_url, echo=True)
    
    try:
        async with engine.begin() as conn:
            # Проверяем, есть ли тайм-слоты с NULL id
            result = await conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM time_slots 
                WHERE id IS NULL
            """))
            null_id_count = result.scalar()
            
            if null_id_count == 0:
                logger.info("Тайм-слотов с NULL id не найдено")
                return True
            
            logger.info(f"Найдено {null_id_count} тайм-слотов с NULL id")
            
            # Удаляем тайм-слоты с NULL id
            result = await conn.execute(text("""
                DELETE FROM time_slots 
                WHERE id IS NULL
            """))
            
            deleted_count = result.rowcount
            logger.info(f"Удалено {deleted_count} тайм-слотов с NULL id")
            
            # Проверяем, что удаление прошло успешно
            result = await conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM time_slots 
                WHERE id IS NULL
            """))
            remaining_null_count = result.scalar()
            
            if remaining_null_count == 0:
                logger.info("✅ Очистка завершена успешно")
                return True
            else:
                logger.warning(f"⚠️ Осталось {remaining_null_count} тайм-слотов с NULL id")
                return False
                
    except Exception as e:
        logger.error(f"Ошибка при очистке тайм-слотов: {e}")
        return False
    finally:
        await engine.dispose()

async def main():
    """Главная функция."""
    logger.info("Начинаем очистку тайм-слотов без ID...")
    
    success = await cleanup_time_slots()
    
    if success:
        logger.info("Скрипт выполнен успешно")
        sys.exit(0)
    else:
        logger.error("Скрипт завершился с ошибками")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

