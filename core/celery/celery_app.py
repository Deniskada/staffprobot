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
        "core.celery.tasks.reminder_tasks",  # Создание напоминаний о сменах
        "core.celery.tasks.task_notifications",
        "core.celery.tasks.shift_tasks", 
        "core.celery.tasks.analytics_tasks",
        "core.celery.tasks.payroll_tasks",
        "core.celery.tasks.adjustment_tasks",  # Phase 4A
        "core.celery.tasks.task_assignment",  # Tasks v2: автоназначение
        "core.celery.tasks.task_bonuses",  # Tasks v2: бонусы/штрафы
        "core.celery.tasks.billing_tasks"  # Iteration 39: биллинг и автопродление подписок
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
        # Создание напоминаний о сменах каждые 5 минут
        'create-shift-reminders': {
            'task': 'create_shift_reminders',
            'schedule': 5 * 60,  # 5 минут
        },
        # Проверка открытия/закрытия объектов каждые 10 минут
        'check-object-openings': {
            'task': 'check_object_openings',
            'schedule': 10 * 60,  # 10 минут
        },
        # Обработка и отправка запланированных уведомлений каждую минуту
        'process-reminders': {
            'task': 'core.celery.tasks.notification_tasks.process_reminders',
            'schedule': 60,  # 1 минута
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
        # Phase 4A: Обработка закрытых смен каждые 10 минут
        'process-closed-shifts-adjustments': {
            'task': 'process_closed_shifts_adjustments',
            'schedule': 600,  # каждые 10 минут
        },
        # Phase 4A: Создание payroll_entries по графикам каждый день в 04:00 (MSK)
        'create-payroll-entries-by-schedule': {
            'task': 'create_payroll_entries_by_schedule',
            'schedule': crontab(hour=4, minute=0),  # каждый день в 04:00 MSK
        },
        # Финальный расчёт при увольнении — в 04:05 (MSK)
        'create-final-settlements-by-termination-date': {
            'task': 'create_final_settlements_by_termination_date',
            'schedule': crontab(hour=4, minute=5),  # каждый день в 04:05 MSK
        },
        # Автоматическое назначение задач на смены — в 04:00 (MSK)
        'auto-assign-tasks': {
            'task': 'auto_assign_tasks',
            'schedule': crontab(hour=4, minute=0),  # каждый день в 04:00 MSK
        },
        # Обработка бонусов/штрафов за задачи v2 — каждые 10 минут
        'process-task-bonuses': {
            'task': 'process_task_bonuses',
            'schedule': 600,  # каждые 10 минут
        },
        # Iteration 39: Проверка подписок, истекающих через 7 и 1 день — ежедневно в 09:00 UTC
        'check-expiring-subscriptions': {
            'task': 'check-expiring-subscriptions',
            'schedule': crontab(hour=9, minute=0),  # ежедневно в 09:00 UTC
        },
        # Iteration 39: Проверка истёкших подписок — ежедневно в 00:05 UTC
        'check-expired-subscriptions': {
            'task': 'check-expired-subscriptions',
            'schedule': crontab(hour=0, minute=5),  # ежедневно в 00:05 UTC
        },
        # Iteration 39: Активация отложенных подписок — каждые 5 минут
        'activate-scheduled-subscriptions': {
            'task': 'activate-scheduled-subscriptions',
            'schedule': 300,  # каждые 5 минут
        },
    },
    
    # Маршрутизация задач
    task_routes={
        'core.celery.tasks.notification_tasks.*': {'queue': 'notifications'},
        'core.celery.tasks.task_notifications.*': {'queue': 'notifications'},
        'core.celery.tasks.reminder_tasks.*': {'queue': 'notifications'},
        'create_shift_reminders': {'queue': 'celery'},
        'check_object_openings': {'queue': 'celery'},
        'notify_tasks_updated': {'queue': 'notifications'},
        'core.celery.tasks.shift_tasks.*': {'queue': 'shifts'},
        'core.celery.tasks.analytics_tasks.*': {'queue': 'analytics'},
        'core.celery.tasks.payroll_tasks.*': {'queue': 'shifts'},  # Используем shifts для payroll
        'core.celery.tasks.adjustment_tasks.*': {'queue': 'shifts'},  # Phase 4A: adjustments
        'core.celery.tasks.task_assignment.*': {'queue': 'shifts'},  # Tasks v2: назначение
        'core.celery.tasks.task_bonuses.*': {'queue': 'shifts'},  # Tasks v2: бонусы
        'process_closed_shifts_adjustments': {'queue': 'shifts'},  # Phase 4A: явно для задачи
        'create_payroll_entries_by_schedule': {'queue': 'shifts'},  # Phase 4A: явно для задачи
        'create_final_settlements_by_termination_date': {'queue': 'shifts'},  # Финальный расчёт при увольнении
        'auto_assign_tasks': {'queue': 'shifts'},  # Tasks v2: авто-назначение задач
        'process_task_bonuses': {'queue': 'shifts'},  # Tasks v2: обработка бонусов
        'core.celery.tasks.billing_tasks.*': {'queue': 'celery'},  # Iteration 39: биллинг задачи
        'check-expiring-subscriptions': {'queue': 'celery'},  # Iteration 39: проверка истекающих подписок
        'check-expired-subscriptions': {'queue': 'celery'},  # Iteration 39: проверка истёкших подписок
        'activate-scheduled-subscriptions': {'queue': 'celery'},  # Iteration 39: активация отложенных подписок
    },
)

# Автоматическое обнаружение задач
celery_app.autodiscover_tasks()

# Логирование запуска Celery
logger.info(f"Celery application configured - broker: {settings.rabbitmq_url}, backend: {settings.redis_url}")
