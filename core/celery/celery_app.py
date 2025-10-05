"""Celery приложение для StaffProBot."""

import os
from celery import Celery
from celery.schedules import crontab
from core.config.settings import settings
from core.logging.logger import logger

# Создание Celery приложения
celery_app = Celery(
    "staffprobot",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=[
        "core.celery.tasks.notification_tasks",
        "core.celery.tasks.shift_tasks", 
        "core.celery.tasks.analytics_tasks"
    ]
)

# Конфигурация Celery
celery_app.conf.update(
    # Часовой пояс
    timezone=settings.default_timezone,
    enable_utc=True,
    
    
    # Сериализация
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Настройки задач
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
    
    # Настройки результатов
    result_expires=3600,  # 1 час
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0
        }
    },
    
    # Настройки worker'а
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Настройки планировщика
    beat_schedule={
        # Проверка напоминаний каждые 30 минут
        'process-reminders': {
            'task': 'core.celery.tasks.notification_tasks.process_reminders',
            'schedule': 30 * 60,  # 30 минут
        },
        # Автоматическое закрытие смен каждые 30 минут
        'auto-close-shifts': {
            'task': 'core.celery.tasks.shift_tasks.auto_close_shifts',
            'schedule': 30 * 60,  # каждые 30 минут
        },
        # Очистка старых кэшей
        'cleanup-cache': {
            'task': 'core.celery.tasks.analytics_tasks.cleanup_cache',
            'schedule': 6 * 60 * 60,  # каждые 6 часов
        },
        # 1 декабря — планирование тайм-слотов на следующий год
        'plan-next-year-timeslots': {
            'task': 'core.celery.tasks.shift_tasks.plan_next_year_timeslots',
            'schedule': crontab(hour=3, minute=0, day_of_month=1, month_of_year=12),  # 1 декабря в 03:00
        },
    },
    
    # Маршрутизация задач
    task_routes={
        'core.celery.tasks.notification_tasks.*': {'queue': 'notifications'},
        'core.celery.tasks.shift_tasks.*': {'queue': 'shifts'},
        'core.celery.tasks.analytics_tasks.*': {'queue': 'analytics'},
    },
)

# Автоматическое обнаружение задач
celery_app.autodiscover_tasks()

# Логирование запуска Celery
logger.info(f"Celery application configured - broker: {settings.rabbitmq_url}, backend: {settings.redis_url}")
