"""Проверка здоровья системы - подключения к БД, Redis и другим сервисам."""

import asyncio
from typing import Dict, Any, List
from core.config.settings import settings
from core.logging.logger import logger


class HealthChecker:
    """Проверка доступности критических сервисов."""
    
    async def check_database(self) -> Dict[str, Any]:
        """Проверка подключения к PostgreSQL."""
        try:
            from core.database.session import DatabaseManager
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            async with db_manager.get_session() as session:
                # Простой запрос для проверки соединения
                result = await session.execute("SELECT 1 as test")
                test_result = result.scalar()
                
                if test_result == 1:
                    logger.info("Database connection successful")
                    return {
                        'service': 'postgresql',
                        'status': 'healthy',
                        'message': 'Database connection successful',
                        'url': settings.database_url.split('@')[1] if '@' in settings.database_url else 'localhost'
                    }
                else:
                    raise Exception("Unexpected database response")
                    
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return {
                'service': 'postgresql',
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}',
                'url': settings.database_url.split('@')[1] if '@' in settings.database_url else 'localhost'
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Проверка подключения к Redis."""
        try:
            from core.cache.redis_cache import cache
            
            # Проверяем подключение к Redis
            if hasattr(cache, 'redis') and cache.redis:
                await cache.redis.ping()
                logger.info("Redis connection successful")
                return {
                    'service': 'redis',
                    'status': 'healthy',
                    'message': 'Redis connection successful',
                    'url': settings.redis_url
                }
            else:
                # Пытаемся подключиться
                await cache.connect()
                await cache.redis.ping()
                logger.info("Redis connection established")
                return {
                    'service': 'redis',
                    'status': 'healthy',
                    'message': 'Redis connection established',
                    'url': settings.redis_url
                }
                
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return {
                'service': 'redis',
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}',
                'url': settings.redis_url
            }
    
    async def check_rabbitmq(self) -> Dict[str, Any]:
        """Проверка подключения к RabbitMQ."""
        try:
            import aio_pika
            
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            await connection.close()
            
            logger.info("RabbitMQ connection successful")
            return {
                'service': 'rabbitmq',
                'status': 'healthy',
                'message': 'RabbitMQ connection successful',
                'url': settings.rabbitmq_url
            }
            
        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            return {
                'service': 'rabbitmq',
                'status': 'unhealthy',
                'message': f'RabbitMQ connection failed: {str(e)}',
                'url': settings.rabbitmq_url
            }
    
    async def check_all_services(self, required_services: List[str] = None) -> Dict[str, Any]:
        """
        Проверка всех сервисов.
        
        Args:
            required_services: Список обязательных сервисов. 
                             Если None, проверяются все доступные.
        
        Returns:
            Результат проверки всех сервисов
        """
        if required_services is None:
            required_services = ['postgresql', 'redis']
        
        results = []
        overall_status = 'healthy'
        
        # Проверка PostgreSQL
        if 'postgresql' in required_services:
            db_result = await self.check_database()
            results.append(db_result)
            if db_result['status'] != 'healthy':
                overall_status = 'unhealthy'
        
        # Проверка Redis
        if 'redis' in required_services:
            redis_result = await self.check_redis()
            results.append(redis_result)
            if redis_result['status'] != 'healthy':
                overall_status = 'degraded'  # Redis не критичен, система может работать
        
        # Проверка RabbitMQ (опционально)
        if 'rabbitmq' in required_services:
            rabbitmq_result = await self.check_rabbitmq()
            results.append(rabbitmq_result)
            if rabbitmq_result['status'] != 'healthy':
                if overall_status == 'healthy':
                    overall_status = 'degraded'  # RabbitMQ не критичен
        
        healthy_count = sum(1 for r in results if r['status'] == 'healthy')
        total_count = len(results)
        
        return {
            'overall_status': overall_status,
            'healthy_services': healthy_count,
            'total_services': total_count,
            'services': results,
            'timestamp': str(asyncio.get_event_loop().time())
        }
    
    async def wait_for_services(self, 
                               required_services: List[str] = None,
                               max_attempts: int = 30,
                               delay: int = 2) -> bool:
        """
        Ожидание доступности сервисов с повторными попытками.
        
        Args:
            required_services: Список обязательных сервисов
            max_attempts: Максимальное количество попыток
            delay: Задержка между попытками в секундах
        
        Returns:
            True если все сервисы доступны, False если превышено время ожидания
        """
        if required_services is None:
            required_services = ['postgresql', 'redis']
        
        logger.info(f"Waiting for services: {', '.join(required_services)}")
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Health check attempt {attempt}/{max_attempts}")
            
            health_result = await self.check_all_services(required_services)
            
            if health_result['overall_status'] in ['healthy', 'degraded']:
                logger.info(f"Services ready after {attempt} attempts")
                return True
            
            # Показываем статус каждого сервиса
            for service in health_result['services']:
                status_emoji = "✅" if service['status'] == 'healthy' else "❌"
                logger.info(f"{status_emoji} {service['service']}: {service['message']}")
            
            if attempt < max_attempts:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        logger.error(f"Services not ready after {max_attempts} attempts")
        return False


# Глобальный экземпляр
health_checker = HealthChecker()
