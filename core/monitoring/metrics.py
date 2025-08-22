"""Prometheus метрики для StaffProBot."""

from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
from typing import Dict, Any
import time
from functools import wraps

from core.config.settings import settings
from core.logging.logger import logger

# Метрики HTTP запросов
http_requests_total = Counter(
    'staffprobot_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'staffprobot_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Метрики базы данных
db_queries_total = Counter(
    'staffprobot_db_queries_total',
    'Total database queries',
    ['table', 'operation']
)

db_query_duration_seconds = Histogram(
    'staffprobot_db_query_duration_seconds',
    'Database query duration in seconds',
    ['table', 'operation']
)

db_connections_active = Gauge(
    'staffprobot_db_connections_active',
    'Active database connections'
)

# Метрики кэша
cache_operations_total = Counter(
    'staffprobot_cache_operations_total',
    'Total cache operations',
    ['operation', 'result']
)

cache_hit_ratio = Gauge(
    'staffprobot_cache_hit_ratio',
    'Cache hit ratio percentage'
)

# Метрики Celery
celery_tasks_total = Counter(
    'staffprobot_celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'staffprobot_celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)

# Метрики бизнес-логики
shifts_total = Counter(
    'staffprobot_shifts_total',
    'Total shifts',
    ['status', 'object_id']
)

users_active = Gauge(
    'staffprobot_users_active',
    'Active users count'
)

objects_total = Gauge(
    'staffprobot_objects_total',
    'Total objects count'
)

# Метрики Telegram бота
bot_messages_total = Counter(
    'staffprobot_bot_messages_total',
    'Total bot messages',
    ['message_type', 'user_id']
)

bot_commands_total = Counter(
    'staffprobot_bot_commands_total',
    'Total bot commands',
    ['command']
)

# Системные метрики
app_info = Info(
    'staffprobot_app_info',
    'Application info'
)

# Инициализация информации о приложении
app_info.info({
    'version': settings.version,
    'environment': settings.environment
})


class MetricsCollector:
    """Коллектор метрик для StaffProBot."""
    
    @staticmethod
    def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
        """Записывает метрики HTTP запроса."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @staticmethod
    def record_db_query(table: str, operation: str, duration: float):
        """Записывает метрики запроса к БД."""
        db_queries_total.labels(
            table=table,
            operation=operation
        ).inc()
        
        db_query_duration_seconds.labels(
            table=table,
            operation=operation
        ).observe(duration)
    
    @staticmethod
    def update_db_connections(count: int):
        """Обновляет количество активных соединений с БД."""
        db_connections_active.set(count)
    
    @staticmethod
    def record_cache_operation(operation: str, result: str):
        """Записывает операцию кэша."""
        cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()
    
    @staticmethod
    def update_cache_hit_ratio(ratio: float):
        """Обновляет коэффициент попаданий в кэш."""
        cache_hit_ratio.set(ratio)
    
    @staticmethod
    def record_celery_task(task_name: str, status: str, duration: float = None):
        """Записывает выполнение Celery задачи."""
        celery_tasks_total.labels(
            task_name=task_name,
            status=status
        ).inc()
        
        if duration is not None:
            celery_task_duration_seconds.labels(
                task_name=task_name
            ).observe(duration)
    
    @staticmethod
    def record_shift(status: str, object_id: int):
        """Записывает создание/изменение смены."""
        shifts_total.labels(
            status=status,
            object_id=str(object_id)
        ).inc()
    
    @staticmethod
    def update_active_users(count: int):
        """Обновляет количество активных пользователей."""
        users_active.set(count)
    
    @staticmethod
    def update_objects_total(count: int):
        """Обновляет общее количество объектов."""
        objects_total.set(count)
    
    @staticmethod
    def record_bot_message(message_type: str, user_id: int):
        """Записывает сообщение бота."""
        bot_messages_total.labels(
            message_type=message_type,
            user_id=str(user_id)
        ).inc()
    
    @staticmethod
    def record_bot_command(command: str):
        """Записывает команду бота."""
        bot_commands_total.labels(command=command).inc()


# Декораторы для автоматического сбора метрик
def monitor_http_request(endpoint: str):
    """Декоратор для мониторинга HTTP запросов."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            start_time = time.time()
            method = request.method
            status_code = 200
            
            try:
                response = await func(request, *args, **kwargs)
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                return response
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                MetricsCollector.record_http_request(method, endpoint, status_code, duration)
        
        return wrapper
    return decorator


def monitor_db_query(table: str, operation: str):
    """Декоратор для мониторинга запросов к БД."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                MetricsCollector.record_db_query(table, operation, duration)
        
        return wrapper
    return decorator


def monitor_celery_task(task_name: str):
    """Декоратор для мониторинга Celery задач."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                raise
            finally:
                duration = time.time() - start_time
                MetricsCollector.record_celery_task(task_name, status, duration)
        
        return wrapper
    return decorator


def start_metrics_server(port: int = None):
    """Запуск HTTP сервера для метрик."""
    metrics_port = port or settings.prometheus_port
    
    try:
        start_http_server(metrics_port)
        logger.info(f"Prometheus metrics server started on port {metrics_port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


# Глобальный экземпляр коллектора
metrics_collector = MetricsCollector()
