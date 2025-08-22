#!/usr/bin/env python3
"""Запуск системы мониторинга."""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.monitoring.metrics import start_metrics_server, metrics_collector
from core.cache.redis_cache import init_cache
from core.database.session import DatabaseManager
from core.logging.logger import logger


async def collect_system_metrics():
    """Сбор системных метрик."""
    try:
        # Инициализируем подключения
        await init_cache()
        db_manager = DatabaseManager()
        
        while True:
            try:
                # Собираем метрики активных пользователей
                async with db_manager.get_session() as session:
                    from apps.api.services.user_service_db import UserServiceDB
                    from apps.api.services.object_service_db import ObjectServiceDB
                    
                    user_service = UserServiceDB(session)
                    object_service = ObjectServiceDB(session)
                    
                    # Подсчитываем активных пользователей
                    active_users = await user_service.get_active_users_count()
                    metrics_collector.update_active_users(active_users)
                    
                    # Подсчитываем общее количество объектов
                    total_objects = await object_service.get_objects_count()
                    metrics_collector.update_objects_total(total_objects)
                    
                    # Обновляем метрики соединений с БД
                    active_connections = await db_manager.get_active_connections_count()
                    metrics_collector.update_db_connections(active_connections)
                
                # Обновляем метрики кэша
                from core.cache.cache_service import CacheService
                cache_stats = await CacheService.get_cache_stats()
                redis_stats = cache_stats.get('redis_stats', {})
                
                if 'hit_rate' in redis_stats:
                    metrics_collector.update_cache_hit_ratio(redis_stats['hit_rate'])
                
                logger.debug("System metrics collected successfully")
                
            except Exception as e:
                logger.error(f"Failed to collect system metrics: {e}")
            
            # Ждем 30 секунд перед следующим сбором
            await asyncio.sleep(30)
            
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")


async def main():
    """Главная функция запуска мониторинга."""
    logger.info("Starting StaffProBot monitoring system")
    
    try:
        # Запускаем HTTP сервер для метрик
        start_metrics_server()
        
        # Запускаем сбор системных метрик
        await collect_system_metrics()
        
    except KeyboardInterrupt:
        logger.info("Monitoring system stopped by user")
    except Exception as e:
        logger.error(f"Monitoring system failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
