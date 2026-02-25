"""
Модуль логирования для StaffProBot
Реализует структурированное JSON логирование
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class JSONFormatter(logging.Formatter):
    """Форматтер для вывода логов в JSON формате"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Добавляем дополнительные поля если есть
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        
        # Добавляем exception info если есть
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class StructuredLogger:
    """Структурированный логгер с дополнительным контекстом"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_context(self, level: int, message: str, **kwargs: Any) -> None:
        """Логирует сообщение с дополнительным контекстом"""
        extra = {}
        for key, value in kwargs.items():
            if value is not None:
                extra[key] = value
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Логирует debug сообщение"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Логирует info сообщение"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Логирует warning сообщение"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Логирует error сообщение"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Логирует critical сообщение"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Логирует exception с traceback"""
        extra = {}
        for key, value in kwargs.items():
            if value is not None:
                extra[key] = value
        
        self.logger.exception(message, extra=extra)

def setup_logging() -> None:
    """Настраивает логирование для приложения"""
    import os
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Используем простой формат для MVP
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Подавляем DEBUG-шум от сторонних библиотек
    for noisy in ("httpcore", "httpx", "telegram", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

# Создаем основной логгер
logger = StructuredLogger("staffprobot")

# Настраиваем логирование при импорте модуля
setup_logging()


