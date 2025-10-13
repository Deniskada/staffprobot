"""Сервис для массовых операций с уведомлениями."""

from typing import List, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from domain.entities.notification import Notification, NotificationStatus
from core.logging.logger import logger
import time


class NotificationBulkService:
    """Сервис для массовых операций с уведомлениями"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def cancel_notifications(self, notification_ids: List[int]) -> int:
        """Массовая отмена уведомлений"""
        try:
            if not notification_ids:
                return 0
            
            # Обновляем статус уведомлений на CANCELLED
            query = update(Notification).where(
                Notification.id.in_(notification_ids),
                Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SCHEDULED])
            ).values(
                status=NotificationStatus.CANCELLED,
                updated_at=func.now()
            )
            
            result = await self.session.execute(query)
            cancelled_count = result.rowcount
            
            await self.session.commit()
            
            logger.info(f"Cancelled {cancelled_count} notifications", notification_ids=notification_ids)
            return cancelled_count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error cancelling notifications: {e}")
            raise Exception(f"Ошибка отмены уведомлений: {str(e)}")

    async def retry_notifications(self, notification_ids: List[int]) -> int:
        """Массовая повторная отправка уведомлений"""
        try:
            if not notification_ids:
                return 0
            
            # Обновляем статус уведомлений на PENDING для повторной отправки
            query = update(Notification).where(
                Notification.id.in_(notification_ids),
                Notification.status.in_([NotificationStatus.FAILED, NotificationStatus.CANCELLED])
            ).values(
                status=NotificationStatus.PENDING,
                error_message=None,
                retry_count=Notification.retry_count + 1,
                updated_at=func.now()
            )
            
            result = await self.session.execute(query)
            retried_count = result.rowcount
            
            await self.session.commit()
            
            logger.info(f"Retried {retried_count} notifications", notification_ids=notification_ids)
            return retried_count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error retrying notifications: {e}")
            raise Exception(f"Ошибка повторной отправки уведомлений: {str(e)}")

    async def delete_notifications(self, notification_ids: List[int]) -> int:
        """Массовое удаление уведомлений"""
        try:
            if not notification_ids:
                return 0
            
            # Удаляем уведомления (мягкое удаление через статус DELETED)
            query = update(Notification).where(
                Notification.id.in_(notification_ids)
            ).values(
                status=NotificationStatus.DELETED,
                updated_at=func.now()
            )
            
            result = await self.session.execute(query)
            deleted_count = result.rowcount
            
            await self.session.commit()
            
            logger.info(f"Deleted {deleted_count} notifications", notification_ids=notification_ids)
            return deleted_count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting notifications: {e}")
            raise Exception(f"Ошибка удаления уведомлений: {str(e)}")

    async def export_notifications(self, notification_ids: List[int], format: str = "csv") -> Dict[str, Any]:
        """Экспорт уведомлений в различных форматах"""
        try:
            if not notification_ids:
                return {
                    "status": "error",
                    "message": "Нет уведомлений для экспорта"
                }
            
            # Получаем уведомления для экспорта
            query = select(Notification).where(Notification.id.in_(notification_ids))
            result = await self.session.execute(query)
            notifications = result.scalars().all()
            
            if format.lower() == "csv":
                export_data = self._export_to_csv(notifications)
            elif format.lower() == "json":
                export_data = self._export_to_json(notifications)
            elif format.lower() == "xlsx":
                export_data = self._export_to_xlsx(notifications)
            else:
                return {
                    "status": "error",
                    "message": f"Неподдерживаемый формат экспорта: {format}"
                }
            
            return {
                "status": "success",
                "message": f"Экспорт выполнен успешно",
                "data": export_data,
                "format": format,
                "count": len(notifications)
            }
            
        except Exception as e:
            logger.error(f"Error exporting notifications: {e}")
            return {
                "status": "error",
                "message": f"Ошибка экспорта: {str(e)}"
            }

    def _export_to_csv(self, notifications: List[Notification]) -> str:
        """Экспорт в CSV формат"""
        try:
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow([
                "ID", "Тип", "Статус", "Канал", "Приоритет", "Пользователь ID",
                "Заголовок", "Содержимое", "Создано", "Отправлено", "Доставлено", "Прочитано", "Ошибка"
            ])
            
            # Данные
            for notification in notifications:
                writer.writerow([
                    notification.id,
                    notification.type.value if notification.type else "",
                    notification.status.value if notification.status else "",
                    notification.channel.value if notification.channel else "",
                    notification.priority.value if notification.priority else "",
                    notification.user_id,
                    notification.subject or "",
                    notification.content or "",
                    notification.created_at.isoformat() if notification.created_at else "",
                    notification.sent_at.isoformat() if notification.sent_at else "",
                    notification.delivered_at.isoformat() if notification.delivered_at else "",
                    notification.read_at.isoformat() if notification.read_at else "",
                    notification.error_message or ""
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return ""

    def _export_to_json(self, notifications: List[Notification]) -> str:
        """Экспорт в JSON формат"""
        try:
            import json
            
            data = []
            for notification in notifications:
                data.append({
                    "id": notification.id,
                    "type": notification.type.value if notification.type else None,
                    "status": notification.status.value if notification.status else None,
                    "channel": notification.channel.value if notification.channel else None,
                    "priority": notification.priority.value if notification.priority else None,
                    "user_id": notification.user_id,
                    "subject": notification.subject,
                    "content": notification.content,
                    "created_at": notification.created_at.isoformat() if notification.created_at else None,
                    "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                    "delivered_at": notification.delivered_at.isoformat() if notification.delivered_at else None,
                    "read_at": notification.read_at.isoformat() if notification.read_at else None,
                    "error_message": notification.error_message
                })
            
            return json.dumps(data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return ""

    def _export_to_xlsx(self, notifications: List[Notification]) -> bytes:
        """Экспорт в XLSX формат"""
        try:
            import pandas as pd
            import io
            
            # Создаем DataFrame
            data = []
            for notification in notifications:
                data.append({
                    "ID": notification.id,
                    "Тип": notification.type.value if notification.type else "",
                    "Статус": notification.status.value if notification.status else "",
                    "Канал": notification.channel.value if notification.channel else "",
                    "Приоритет": notification.priority.value if notification.priority else "",
                    "Пользователь ID": notification.user_id,
                    "Заголовок": notification.subject or "",
                    "Содержимое": notification.content or "",
                    "Создано": notification.created_at.isoformat() if notification.created_at else "",
                    "Отправлено": notification.sent_at.isoformat() if notification.sent_at else "",
                    "Доставлено": notification.delivered_at.isoformat() if notification.delivered_at else "",
                    "Прочитано": notification.read_at.isoformat() if notification.read_at else "",
                    "Ошибка": notification.error_message or ""
                })
            
            df = pd.DataFrame(data)
            
            # Сохраняем в XLSX
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Уведомления', index=False)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting to XLSX: {e}")
            return b""

    async def get_bulk_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Получение статуса массовой операции"""
        try:
            # Заглушка для статуса операций
            # В реальной реализации здесь будет запрос к таблице операций
            return {
                "operation_id": operation_id,
                "status": "completed",
                "progress": 100,
                "total_items": 100,
                "processed_items": 100,
                "failed_items": 0,
                "started_at": "2024-01-01T10:00:00Z",
                "completed_at": "2024-01-01T10:05:00Z",
                "errors": []
            }
            
        except Exception as e:
            logger.error(f"Error getting bulk operation status: {e}")
            return {
                "operation_id": operation_id,
                "status": "error",
                "message": f"Ошибка получения статуса: {str(e)}"
            }

    async def schedule_bulk_operation(
        self,
        operation_type: str,
        notification_ids: List[int],
        scheduled_at: str = None
    ) -> Dict[str, Any]:
        """Планирование массовой операции"""
        try:
            if not notification_ids:
                return {
                    "status": "error",
                    "message": "Нет уведомлений для обработки"
                }
            
            # Валидация типа операции
            valid_operations = ["cancel", "retry", "delete", "export"]
            if operation_type not in valid_operations:
                return {
                    "status": "error",
                    "message": f"Неподдерживаемый тип операции: {operation_type}"
                }
            
            # Здесь будет создание задачи в Celery или другой очереди
            operation_id = f"{operation_type}_{len(notification_ids)}_{int(time.time())}"
            
            return {
                "status": "success",
                "message": "Массовая операция запланирована",
                "operation_id": operation_id,
                "operation_type": operation_type,
                "notification_count": len(notification_ids),
                "scheduled_at": scheduled_at
            }
            
        except Exception as e:
            logger.error(f"Error scheduling bulk operation: {e}")
            return {
                "status": "error",
                "message": f"Ошибка планирования операции: {str(e)}"
            }

