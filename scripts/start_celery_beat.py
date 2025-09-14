#!/usr/bin/env python3
"""Запуск Celery beat (планировщик)."""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.celery.celery_app import celery_app
from core.logging.logger import logger

if __name__ == "__main__":
    logger.info("Starting Celery beat scheduler")
    
    # Удаляем старый pidfile если существует
    import os
    pidfile_path = '/tmp/celerybeat.pid'
    if os.path.exists(pidfile_path):
        try:
            os.remove(pidfile_path)
            logger.info("Removed old pidfile")
        except Exception as e:
            logger.warning(f"Could not remove old pidfile: {e}")
    
    # Запуск Celery beat
    celery_app.start([
        'beat',
        '--loglevel=info',
        '--schedule=/tmp/celerybeat-schedule',
        '--pidfile=/tmp/celerybeat.pid'
    ])
