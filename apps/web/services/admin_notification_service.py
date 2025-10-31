"""Сервис для админской аналитики уведомлений."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, text, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache.redis_cache import cached
from domain.entities.notification import Notification, NotificationType, NotificationStatus, NotificationChannel
from domain.entities.payment_notification import PaymentNotification
from domain.entities.user import User
from shared.services.notification_service import NotificationService
from core.logging.logger import logger


class AdminNotificationService(NotificationService):
    """Расширение существующего NotificationService для админской аналитики"""

    def __init__(self, session: AsyncSession):
        # Не вызываем super().__init__(), так как базовый класс не принимает параметры
        self.session = session

    @cached(ttl=timedelta(minutes=10), key_prefix="admin_notifications_stats")
    async def get_notifications_stats(self) -> Dict[str, Any]:
        """Получение общей статистики уведомлений (включая PaymentNotification)"""
        try:
            # Общее количество из таблицы notifications
            total_query = select(func.count(Notification.id))
            total_result = await self.session.execute(total_query)
            total = total_result.scalar() or 0

            # Количество по статусам
            status_query = select(
                Notification.status,
                func.count(Notification.id).label('count')
            ).group_by(Notification.status)
            status_result = await self.session.execute(status_query)
            status_stats = {row.status.value: row.count for row in status_result}

            # Количество по каналам
            channel_query = select(
                Notification.channel,
                func.count(Notification.id).label('count')
            ).group_by(Notification.channel)
            channel_result = await self.session.execute(channel_query)
            channel_stats = {row.channel.value: row.count for row in channel_result}

            # Количество по типам
            type_query = select(
                Notification.type,
                func.count(Notification.id).label('count')
            ).group_by(Notification.type)
            type_result = await self.session.execute(type_query)
            type_stats = {row.type.value: row.count for row in type_result}

            # Статистика PaymentNotification
            payment_total_query = select(func.count(PaymentNotification.id))
            payment_total_result = await self.session.execute(payment_total_query)
            payment_total = payment_total_result.scalar() or 0

            return {
                "total_notifications": total,
                "total_payment_notifications": payment_total,
                "status_stats": status_stats,
                "channel_stats": channel_stats,
                "type_stats": type_stats,
                "last_updated": datetime.now()
            }
        except Exception as e:
            logger.error(f"Error getting notifications stats: {e}")
            return {
                "total_notifications": 0,
                "total_payment_notifications": 0,
                "status_stats": {},
                "channel_stats": {},
                "type_stats": {},
                "last_updated": datetime.now()
            }

    @cached(ttl=timedelta(minutes=15), key_prefix="admin_channel_stats")
    async def get_channel_stats(self) -> Dict[str, Any]:
        """Статистика по каналам доставки"""
        try:
            # Delivery rate по каналам
            delivery_query = select(
                Notification.channel,
                func.count(Notification.id).label('total'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.DELIVERED).label('delivered'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.FAILED).label('failed')
            ).group_by(Notification.channel)
            
            delivery_result = await self.session.execute(delivery_query)
            channel_stats = {}
            
            for row in delivery_result:
                total = row.total or 0
                delivered = row.delivered or 0
                failed = row.failed or 0
                
                delivery_rate = (delivered / total * 100) if total > 0 else 0
                error_rate = (failed / total * 100) if total > 0 else 0
                
                channel_stats[row.channel.value] = {
                    "total": total,
                    "delivered": delivered,
                    "failed": failed,
                    "delivery_rate": round(delivery_rate, 2),
                    "error_rate": round(error_rate, 2)
                }

            return channel_stats
        except Exception as e:
            logger.error(f"Error getting channel stats: {e}")
            return {}

    @cached(ttl=timedelta(minutes=15), key_prefix="admin_type_stats")
    async def get_type_stats(self) -> Dict[str, Any]:
        """Статистика по типам уведомлений"""
        try:
            # Популярность и эффективность по типам
            type_query = select(
                Notification.type,
                func.count(Notification.id).label('total'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.DELIVERED).label('delivered'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.READ).label('read')
            ).group_by(Notification.type)
            
            type_result = await self.session.execute(type_query)
            type_stats = {}
            
            for row in type_result:
                total = row.total or 0
                delivered = row.delivered or 0
                read = row.read or 0
                
                delivery_rate = (delivered / total * 100) if total > 0 else 0
                read_rate = (read / total * 100) if total > 0 else 0
                
                type_stats[row.type.value] = {
                    "total": total,
                    "delivered": delivered,
                    "read": read,
                    "delivery_rate": round(delivery_rate, 2),
                    "read_rate": round(read_rate, 2)
                }

            return type_stats
        except Exception as e:
            logger.error(f"Error getting type stats: {e}")
            return {}

    async def get_recent_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних уведомлений"""
        try:
            query = select(Notification).options(
                selectinload(Notification.user)
            ).order_by(desc(Notification.created_at)).limit(limit)
            
            result = await self.session.execute(query)
            notifications = result.scalars().all()
            
            return [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "status": n.status.value,
                    "channel": n.channel.value,
                    "user_id": n.user_id,
                    "user_name": f"{n.user.first_name} {n.user.last_name}" if n.user else "Неизвестный",
                    "created_at": n.created_at,
                    "sent_at": n.sent_at,
                    "delivered_at": n.read_at,  # Используем read_at как delivered_at
                    "read_at": n.read_at,
                    "subject": n.title,  # Используем title как subject
                    "content": n.content[:100] + "..." if len(n.content) > 100 else n.content
                }
                for n in notifications
            ]
        except Exception as e:
            logger.error(f"Error getting recent notifications: {e}")
            return []

    async def get_notifications_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
        channel_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        user_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Получение уведомлений с пагинацией и фильтрами"""
        try:
            # Базовый запрос
            query = select(Notification).options(selectinload(Notification.user))
            count_query = select(func.count(Notification.id))
            
            # Применяем фильтры
            conditions = []
            
            if status_filter:
                try:
                    status = NotificationStatus(status_filter)
                    conditions.append(Notification.status == status)
                except ValueError:
                    pass
            
            if channel_filter:
                try:
                    channel = NotificationChannel(channel_filter)
                    conditions.append(Notification.channel == channel)
                except ValueError:
                    pass
            
            if type_filter:
                try:
                    notification_type = NotificationType(type_filter)
                    conditions.append(Notification.type == notification_type)
                except ValueError:
                    pass
            
            if user_id:
                conditions.append(Notification.user_id == user_id)
            
            if date_from:
                conditions.append(Notification.created_at >= date_from)
            
            if date_to:
                conditions.append(Notification.created_at <= date_to)
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Получаем общее количество
            total_result = await self.session.execute(count_query)
            total_count = total_result.scalar() or 0
            
            # Применяем пагинацию и сортировку
            offset = (page - 1) * per_page
            query = query.order_by(desc(Notification.created_at)).offset(offset).limit(per_page)
            
            # Выполняем запрос
            result = await self.session.execute(query)
            notifications = result.scalars().all()
            
            # Формируем результат
            notifications_data = [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "status": n.status.value,
                    "channel": n.channel.value,
                    "priority": n.priority.value if n.priority else None,
                    "user_id": n.user_id,
                    "user_name": f"{n.user.first_name} {n.user.last_name}" if n.user else "Неизвестный",
                    "created_at": n.created_at,
                    "sent_at": n.sent_at,
                    "delivered_at": n.read_at,  # Используем read_at как delivered_at
                    "read_at": n.read_at,
                    "title": n.title,  # Добавляем title для шаблона
                    "subject": n.title,  # Используем title как subject (для совместимости)
                    "content": n.message[:200] + "..." if len(n.message) > 200 else n.message,
                    "error_message": n.error_message
                }
                for n in notifications
            ]
            
            return notifications_data, total_count
            
        except Exception as e:
            logger.error(f"Error getting paginated notifications: {e}")
            return [], 0

    async def get_filter_options(self) -> Dict[str, List[str]]:
        """Получение доступных опций для фильтров"""
        try:
            # Статусы
            status_query = select(Notification.status).distinct()
            status_result = await self.session.execute(status_query)
            statuses = [row.status.value for row in status_result]
            
            # Каналы
            channel_query = select(Notification.channel).distinct()
            channel_result = await self.session.execute(channel_query)
            channels = [row.channel.value for row in channel_result]
            
            # Типы
            type_query = select(Notification.type).distinct()
            type_result = await self.session.execute(type_query)
            types = [row.type.value for row in type_result]
            
            return {
                "statuses": statuses,
                "channels": channels,
                "types": types
            }
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {"statuses": [], "channels": [], "types": []}

    async def get_detailed_analytics(self, period: timedelta) -> Dict[str, Any]:
        """Детальная аналитика за период"""
        try:
            start_date = datetime.now() - period
            
            # Общая статистика за период
            period_query = select(
                func.count(Notification.id).label('total'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.DELIVERED).label('delivered'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.READ).label('read'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.FAILED).label('failed')
            ).where(Notification.created_at >= start_date)
            
            period_result = await self.session.execute(period_query)
            period_row = period_result.first()
            
            total = period_row.total or 0
            delivered = period_row.delivered or 0
            read = period_row.read or 0
            failed = period_row.failed or 0
            
            delivery_rate = (delivered / total * 100) if total > 0 else 0
            read_rate = (read / total * 100) if total > 0 else 0
            error_rate = (failed / total * 100) if total > 0 else 0
            
            return {
                "period_days": period.days,
                "total": total,
                "delivered": delivered,
                "read": read,
                "failed": failed,
                "delivery_rate": round(delivery_rate, 2),
                "read_rate": round(read_rate, 2),
                "error_rate": round(error_rate, 2)
            }
        except Exception as e:
            logger.error(f"Error getting detailed analytics: {e}")
            return {}

    async def get_trends(self, period: timedelta) -> Dict[str, List[Dict[str, Any]]]:
        """Получение трендов за период"""
        try:
            start_date = datetime.now() - period
            
            # Тренды по дням
            daily_query = select(
                func.date(Notification.created_at).label('date'),
                func.count(Notification.id).label('count'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.DELIVERED).label('delivered')
            ).where(
                Notification.created_at >= start_date
            ).group_by(
                func.date(Notification.created_at)
            ).order_by('date')
            
            daily_result = await self.session.execute(daily_query)
            daily_trends = [
                {
                    "date": row.date.isoformat(),
                    "total": row.count,
                    "delivered": row.delivered,
                    "delivery_rate": round((row.delivered / row.count * 100) if row.count > 0 else 0, 2)
                }
                for row in daily_result
            ]
            
            return {
                "daily": daily_trends
            }
        except Exception as e:
            logger.error(f"Error getting trends: {e}")
            return {"daily": []}

    async def get_top_users_by_notifications(self, period: timedelta, limit: int = 10) -> List[Dict[str, Any]]:
        """Топ пользователей по количеству уведомлений"""
        try:
            start_date = datetime.now() - period
            
            query = select(
                Notification.user_id,
                User.first_name,
                User.last_name,
                func.count(Notification.id).label('notification_count'),
                func.count(Notification.id).filter(Notification.status == NotificationStatus.READ).label('read_count')
            ).join(
                User, Notification.user_id == User.id
            ).where(
                Notification.created_at >= start_date
            ).group_by(
                Notification.user_id, User.first_name, User.last_name
            ).order_by(
                desc('notification_count')
            ).limit(limit)
            
            result = await self.session.execute(query)
            
            return [
                {
                    "user_id": row.user_id,
                    "user_name": f"{row.first_name} {row.last_name}",
                    "notification_count": row.notification_count,
                    "read_count": row.read_count,
                    "read_rate": round((row.read_count / row.notification_count * 100) if row.notification_count > 0 else 0, 2)
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []

    async def send_test_notification(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка тестового уведомления"""
        try:
            # Здесь можно добавить логику отправки тестового уведомления
            # Пока возвращаем заглушку
            return {
                "status": "success",
                "message": "Тестовое уведомление отправлено",
                "test_data": test_data
            }
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            raise Exception(f"Ошибка отправки тестового уведомления: {str(e)}")

    # ========================================================================
    # МЕТОДЫ ДЛЯ ОДИНОЧНЫХ ОПЕРАЦИЙ (Iteration 25, Phase 2)
    # ========================================================================

    async def get_notification_by_id(self, notification_id: int) -> Optional[Notification]:
        """Получение уведомления по ID"""
        try:
            query = select(Notification).where(Notification.id == notification_id)
            result = await self.session.execute(query)
            notification = result.scalar_one_or_none()
            return notification
        except Exception as e:
            logger.error(f"Error getting notification by ID: {e}")
            return None

    async def retry_notification(self, notification_id: int) -> bool:
        """Повторная отправка уведомления"""
        try:
            # Получаем уведомление
            notification = await self.get_notification_by_id(notification_id)
            if not notification:
                raise ValueError(f"Notification {notification_id} not found")

            # Проверяем, можно ли повторить отправку
            retry_count = notification.retry_count or 0
            if retry_count >= 3:  # Максимум 3 попытки
                logger.warning(f"Notification {notification_id} exceeded max retries")
                return False

            # Сбрасываем статус и счетчик попыток
            notification.status = NotificationStatus.PENDING
            notification.retry_count = retry_count + 1
            notification.error_message = None
            notification.sent_at = None

            await self.session.commit()

            logger.info(f"Notification {notification_id} reset for retry")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error retrying notification: {e}")
            raise

    async def cancel_notification(self, notification_id: int) -> bool:
        """Отмена уведомления"""
        try:
            # Получаем уведомление
            notification = await self.get_notification_by_id(notification_id)
            if not notification:
                raise ValueError(f"Notification {notification_id} not found")

            # Проверяем, можно ли отменить уведомление
            if notification.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ]:
                logger.warning(f"Notification {notification_id} already sent, cannot cancel")
                return False

            # Устанавливаем статус "отменено"
            notification.status = NotificationStatus.CANCELLED

            await self.session.commit()

            logger.info(f"Notification {notification_id} cancelled")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error cancelling notification: {e}")
            raise

    async def get_notification_statistics(self) -> Dict[str, Any]:
        """Получение общей статистики уведомлений"""
        try:
            # Общее количество уведомлений
            total_query = select(func.count(Notification.id))
            total_result = await self.session.execute(total_query)
            total_count = total_result.scalar() or 0
            
            # Убеждаемся, что total_count - это число, а не корутина
            if hasattr(total_count, '__await__'):
                total_count = 0

            # Статистика по статусам
            status_query = select(
                Notification.status,
                func.count(Notification.id).label('count')
            ).group_by(Notification.status)
            status_result = await self.session.execute(status_query)
            status_stats = {row.status.value: row.count for row in status_result}

            # Статистика по каналам
            channel_query = select(
                Notification.channel,
                func.count(Notification.id).label('count')
            ).group_by(Notification.channel)
            channel_result = await self.session.execute(channel_query)
            channel_stats = {row.channel.value: row.count for row in channel_result}

            # Статистика по типам
            type_query = select(
                Notification.type,
                func.count(Notification.id).label('count')
            ).group_by(Notification.type)
            type_result = await self.session.execute(type_query)
            type_stats = {row.type.value: row.count for row in type_result}

            # Успешность доставки
            success_rate = 0
            if total_count > 0:
                success_count = status_stats.get('sent', 0) + status_stats.get('delivered', 0) + status_stats.get('read', 0)
                success_rate = round((success_count / total_count) * 100, 2)

            return {
                "total_notifications": total_count,
                "status_breakdown": status_stats,
                "channel_breakdown": channel_stats,
                "type_breakdown": type_stats,
                "success_rate": success_rate
            }

        except Exception as e:
            logger.error(f"Error getting notification statistics: {e}")
            return {
                "total_notifications": 0,
                "status_breakdown": {},
                "channel_breakdown": {},
                "type_breakdown": {},
                "success_rate": 0
            }

    async def get_channel_statistics(self) -> Dict[str, int]:
        """Получение статистики по каналам"""
        try:
            query = select(
                Notification.channel,
                func.count(Notification.id).label('count')
            ).group_by(Notification.channel)
            
            result = await self.session.execute(query)
            return {row.channel.value: row.count for row in result}

        except Exception as e:
            logger.error(f"Error getting channel statistics: {e}")
            return {}

    async def get_type_statistics(self) -> Dict[str, int]:
        """Получение статистики по типам"""
        try:
            query = select(
                Notification.type,
                func.count(Notification.id).label('count')
            ).group_by(Notification.type)
            
            result = await self.session.execute(query)
            return {row.type.value: row.count for row in result}

        except Exception as e:
            logger.error(f"Error getting type statistics: {e}")
            return {}

    async def get_daily_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Получение ежедневной статистики за последние N дней"""
        try:
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            query = select(
                func.date(Notification.created_at).label('date'),
                func.count(Notification.id).label('count'),
                Notification.status
            ).where(
                Notification.created_at >= start_date
            ).group_by(
                func.date(Notification.created_at),
                Notification.status
            ).order_by(func.date(Notification.created_at))
            
            result = await self.session.execute(query)
            
            # Группируем по датам
            daily_stats = {}
            for row in result:
                date_str = row.date.strftime('%Y-%m-%d')
                if date_str not in daily_stats:
                    daily_stats[date_str] = {'date': date_str, 'total': 0, 'by_status': {}}
                
                daily_stats[date_str]['total'] += row.count
                daily_stats[date_str]['by_status'][row.status.value] = row.count
            
            return list(daily_stats.values())

        except Exception as e:
            logger.error(f"Error getting daily statistics: {e}")
            return []

    async def get_user_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение статистики по пользователям"""
        try:
            query = select(
                Notification.user_id,
                User.first_name,
                User.last_name,
                func.count(Notification.id).label('notification_count'),
                func.count(case(
                    (Notification.status.in_([NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ]), 1)
                )).label('successful_count')
            ).join(
                User, Notification.user_id == User.id
            ).group_by(
                Notification.user_id, User.first_name, User.last_name
            ).order_by(
                func.count(Notification.id).desc()
            ).limit(limit)
            
            result = await self.session.execute(query)
            
            user_stats = []
            for row in result:
                success_rate = 0
                if row.notification_count > 0:
                    success_rate = round((row.successful_count / row.notification_count) * 100, 2)
                
                user_stats.append({
                    "user_id": row.user_id,
                    "user_name": f"{row.first_name} {row.last_name}",
                    "notification_count": row.notification_count,
                    "successful_count": row.successful_count,
                    "success_rate": success_rate
                })
            
            return user_stats

        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return []

    async def export_notifications(
        self,
        format: str = "json",
        status_filter: Optional[str] = None,
        channel_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Экспорт уведомлений в различных форматах"""
        try:
            # Получаем уведомления с фильтрами
            notifications, _ = await self.get_notifications_paginated(
                page=1,
                per_page=10000,  # Большое число для получения всех
                status_filter=status_filter,
                channel_filter=channel_filter,
                type_filter=type_filter,
                date_from=date_from,
                date_to=date_to
            )
            
            if format.lower() == "json":
                return {
                    "format": "json",
                    "data": notifications,
                    "count": len(notifications)
                }
            elif format.lower() == "xlsx":
                # Для Excel экспорта нужно будет добавить pandas
                return {
                    "format": "xlsx",
                    "data": notifications,
                    "count": len(notifications),
                    "message": "Excel export requires pandas library"
                }
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Error exporting notifications: {e}")
            raise

