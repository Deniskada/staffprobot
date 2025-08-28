"""Celery задачи для аналитики и отчетов."""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import Task

from core.celery.celery_app import celery_app
from core.logging.logger import logger
from core.cache.cache_service import CacheService


class AnalyticsTask(Task):
    """Базовый класс для задач аналитики."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Обработка ошибок задач."""
        logger.error(
            f"Analytics task failed: {self.name}",
            task_id=task_id,
            error=str(exc),
            args=args,
            kwargs=kwargs
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Обработка успешного выполнения."""
        logger.info(
            f"Analytics task completed: {self.name}",
            task_id=task_id,
            result=retval
        )


@celery_app.task(base=AnalyticsTask, bind=True)
def generate_report_async(self, user_id: int, report_type: str, params: Dict[str, Any]):
    """Асинхронная генерация отчета."""
    try:
        from apps.analytics.analytics_service import AnalyticsService
        from apps.analytics.export_service import ExportService
        from core.database.session import DatabaseManager
        
        db_manager = DatabaseManager()
        
        async def _generate_report():
            async with db_manager.get_session() as session:
                analytics_service = AnalyticsService(session)
                export_service = ExportService()
                
                # Генерируем данные отчета
                if report_type == "object_report":
                    report_data = await analytics_service.get_object_report(
                        object_id=params.get('object_id'),
                        start_date=datetime.fromisoformat(params.get('start_date')),
                        end_date=datetime.fromisoformat(params.get('end_date'))
                    )
                elif report_type == "user_report":
                    report_data = await analytics_service.get_user_report(
                        user_id=params.get('report_user_id', user_id),
                        start_date=datetime.fromisoformat(params.get('start_date')),
                        end_date=datetime.fromisoformat(params.get('end_date'))
                    )
                elif report_type == "dashboard":
                    report_data = await analytics_service.get_dashboard_data(
                        user_id=user_id
                    )
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
                
                # Экспортируем отчет в нужный формат
                export_format = params.get('format', 'text')
                file_path = None
                
                if export_format == 'pdf':
                    file_path = await export_service.export_to_pdf(
                        report_data, 
                        report_type
                    )
                elif export_format == 'excel':
                    file_path = await export_service.export_to_excel(
                        report_data, 
                        report_type
                    )
                
                return {
                    'report_data': report_data,
                    'file_path': file_path,
                    'export_format': export_format
                }
        
        import asyncio
        result = asyncio.run(_generate_report())
        
        # Отправляем уведомление с готовым отчетом
        from core.celery.tasks.notification_tasks import send_report_notification
        send_report_notification.delay(
            user_id=user_id,
            report_data=result['report_data'],
            report_file_path=result['file_path']
        )
        
        logger.info(
            "Report generated and sent",
            user_id=user_id,
            report_type=report_type,
            has_file=bool(result['file_path'])
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Failed to generate report: {e}",
            user_id=user_id,
            report_type=report_type,
            error=str(e)
        )
        raise


@celery_app.task(base=AnalyticsTask, bind=True)
def update_analytics_cache(self, cache_keys: List[str] = None):
    """Обновление кэша аналитических данных."""
    try:
        from apps.analytics.analytics_service import AnalyticsService
        from core.database.session import DatabaseManager
        
        db_manager = DatabaseManager()
        
        async def _update_cache():
            async with db_manager.get_session() as session:
                analytics_service = AnalyticsService(session)
                
                updated_count = 0
                
                # Если ключи не указаны, обновляем основные метрики
                if not cache_keys:
                    cache_keys_to_update = [
                        "dashboard_stats",
                        "top_objects",
                        "recent_shifts",
                        "monthly_stats"
                    ]
                else:
                    cache_keys_to_update = cache_keys
                
                for cache_key in cache_keys_to_update:
                    try:
                        if cache_key == "dashboard_stats":
                            # Обновляем общие статистики дашборда
                            stats = await analytics_service.get_general_stats()
                            await CacheService.set_analytics_data(
                                cache_key, 
                                stats, 
                                ttl=CacheService.LONG_TTL
                            )
                        
                        elif cache_key == "top_objects":
                            # Обновляем топ объектов
                            top_objects = await analytics_service.get_top_objects()
                            await CacheService.set_analytics_data(
                                cache_key, 
                                top_objects, 
                                ttl=CacheService.LONG_TTL
                            )
                        
                        elif cache_key == "recent_shifts":
                            # Обновляем недавние смены
                            recent_shifts = await analytics_service.get_recent_shifts()
                            await CacheService.set_analytics_data(
                                cache_key, 
                                recent_shifts, 
                                ttl=CacheService.SHORT_TTL
                            )
                        
                        elif cache_key == "monthly_stats":
                            # Обновляем месячную статистику
                            monthly_stats = await analytics_service.get_monthly_stats()
                            await CacheService.set_analytics_data(
                                cache_key, 
                                monthly_stats, 
                                ttl=CacheService.LONG_TTL
                            )
                        
                        updated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to update cache key {cache_key}: {e}")
                
                return updated_count
        
        import asyncio
        updated_count = asyncio.run(_update_cache())
        
        logger.info(f"Updated {updated_count} analytics cache keys")
        return {"updated_count": updated_count}
        
    except Exception as e:
        logger.error(f"Failed to update analytics cache: {e}")
        raise


@celery_app.task(base=AnalyticsTask, bind=True)
def cleanup_cache(self):
    """Очистка устаревших кэшей."""
    try:
        import asyncio
        
        async def _cleanup_cache():
            # Очищаем устаревшие аналитические кэши
            await CacheService.clear_analytics_cache()
            
            # Получаем статистику кэша
            cache_stats = await CacheService.get_cache_stats()
            
            return cache_stats
        
        # Запускаем async функцию
        cache_stats = asyncio.run(_cleanup_cache())
        
        logger.info(
            "Cache cleanup completed",
            redis_stats=cache_stats.get('redis_stats', {}),
            key_counts=cache_stats.get('key_counts', {})
        )
        
        return cache_stats
        
    except Exception as e:
        logger.error(f"Failed to cleanup cache: {e}")
        raise


@celery_app.task(base=AnalyticsTask, bind=True)
def calculate_monthly_metrics(self, year: int = None, month: int = None):
    """Расчет месячных метрик."""
    try:
        from apps.analytics.analytics_service import AnalyticsService
        from core.database.session import DatabaseManager
        
        if not year or not month:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        db_manager = DatabaseManager()
        
        async def _calculate_metrics():
            async with db_manager.get_session() as session:
                analytics_service = AnalyticsService(session)
                
                # Рассчитываем метрики за месяц
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
                
                metrics = await analytics_service.calculate_period_metrics(
                    start_date, 
                    end_date
                )
                
                # Сохраняем в кэш
                cache_key = f"monthly_metrics_{year}_{month}"
                await CacheService.set_analytics_data(
                    cache_key, 
                    metrics, 
                    ttl=timedelta(days=30)  # Кэшируем на месяц
                )
                
                return metrics
        
        import asyncio
        metrics = asyncio.run(_calculate_metrics())
        
        logger.info(
            "Monthly metrics calculated",
            year=year,
            month=month,
            total_shifts=metrics.get('total_shifts', 0),
            total_hours=metrics.get('total_hours', 0)
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to calculate monthly metrics: {e}")
        raise


@celery_app.task(base=AnalyticsTask, bind=True)
def generate_scheduled_reports(self):
    """Генерация запланированных отчетов."""
    try:
        from core.database.session import DatabaseManager
        from apps.api.services.user_service_db import UserServiceDB
        
        db_manager = DatabaseManager()
        
        async def _generate_reports():
            async with db_manager.get_session() as session:
                user_service = UserServiceDB(session)
                
                # Получаем всех владельцев объектов
                owners = await user_service.get_users_by_role("owner")
                
                generated_count = 0
                for owner in owners:
                    try:
                        # Генерируем еженедельный отчет
                        generate_report_async.delay(
                            user_id=owner.id,
                            report_type="dashboard",
                            params={
                                'start_date': (datetime.now() - timedelta(days=7)).isoformat(),
                                'end_date': datetime.now().isoformat(),
                                'format': 'pdf'
                            }
                        )
                        generated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to schedule report for owner {owner.id}: {e}")
                
                return generated_count
        
        import asyncio
        generated_count = asyncio.run(_generate_reports())
        
        logger.info(f"Scheduled {generated_count} reports")
        return {"generated_count": generated_count}
        
    except Exception as e:
        logger.error(f"Failed to generate scheduled reports: {e}")
        raise
