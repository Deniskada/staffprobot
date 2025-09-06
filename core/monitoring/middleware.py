"""Middleware для сбора метрик."""

import time
from typing import Callable, Any
from functools import wraps

from core.monitoring.metrics import metrics_collector
from core.logging.logger import logger


class MonitoringMiddleware:
    """Middleware для автоматического сбора метрик."""
    
    def __init__(self):
        self.metrics = metrics_collector
    
    def http_middleware(self, endpoint: str):
        """HTTP middleware для сбора метрик запросов."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                start_time = time.time()
                method = getattr(request, 'method', 'GET')
                status_code = 200
                
                try:
                    response = await func(request, *args, **kwargs)
                    
                    # Извлекаем код ответа
                    if hasattr(response, 'status_code'):
                        status_code = response.status_code
                    elif hasattr(response, 'status'):
                        status_code = response.status
                    
                    return response
                    
                except Exception as e:
                    status_code = 500
                    logger.error(f"HTTP request failed: {e}, endpoint={endpoint}, method={method}")
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    self.metrics.record_http_request(method, endpoint, status_code, duration)
            
            return wrapper
        return decorator
    
    def database_middleware(self, table: str, operation: str):
        """Database middleware для сбора метрик запросов к БД."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    logger.error(f"Database query failed: {e}, table={table}, operation={operation}")
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    self.metrics.record_db_query(table, operation, duration)
            
            return wrapper
        return decorator
    
    def cache_middleware(self, operation: str):
        """Cache middleware для сбора метрик кэша."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                result_status = "hit"
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Определяем результат операции
                    if operation == "get" and result is None:
                        result_status = "miss"
                    elif operation in ["set", "delete"]:
                        result_status = "success" if result else "failure"
                    
                    return result
                    
                except Exception as e:
                    result_status = "error"
                    logger.error(f"Cache operation failed: {e}, operation={operation}")
                    raise
                    
                finally:
                    self.metrics.record_cache_operation(operation, result_status)
            
            return wrapper
        return decorator
    
    def bot_middleware(self, message_type: str):
        """Bot middleware для сбора метрик бота."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(update, context, *args, **kwargs):
                user_id = update.effective_user.id if update.effective_user else 0
                
                try:
                    result = await func(update, context, *args, **kwargs)
                    self.metrics.record_bot_message(message_type, user_id)
                    return result
                    
                except Exception as e:
                    logger.error(f"Bot handler failed: {e}, message_type={message_type}, user_id={user_id}")
                    raise
            
            return wrapper
        return decorator


# Глобальный экземпляр middleware
monitoring_middleware = MonitoringMiddleware()
