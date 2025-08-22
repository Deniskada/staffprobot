#!/usr/bin/env python3
"""Запуск Celery worker."""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.celery.celery_app import celery_app
from core.logging.logger import logger

if __name__ == "__main__":
    logger.info("Starting Celery worker")
    
    # Запуск Celery worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--queues=notifications,shifts,analytics',
        '--concurrency=4',
        '--max-tasks-per-child=1000'
    ])
