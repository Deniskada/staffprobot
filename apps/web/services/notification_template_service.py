"""Сервис для управления шаблонами уведомлений через веб-интерфейс."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.notification import NotificationType, NotificationChannel
from shared.templates.notifications.base_templates import NotificationTemplateManager
from core.logging.logger import logger


class NotificationTemplateService:
    """Сервис для управления шаблонами уведомлений через веб-интерфейс"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.template_manager = NotificationTemplateManager()

    async def get_templates_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        type_filter: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Получение шаблонов с пагинацией и фильтрами"""
        try:
            # Получаем все доступные шаблоны
            all_templates = self.template_manager.ALL_TEMPLATES
            
            # Применяем фильтр по типу
            if type_filter:
                try:
                    notification_type = NotificationType(type_filter)
                    filtered_templates = {notification_type: all_templates.get(notification_type)}
                    filtered_templates = {k: v for k, v in filtered_templates.items() if v is not None}
                except ValueError:
                    filtered_templates = {}
            else:
                filtered_templates = all_templates
            
            # Преобразуем в список для пагинации
            templates_list = []
            for notification_type, template_data in filtered_templates.items():
                templates_list.append({
                    "id": notification_type.value,
                    "type": notification_type.value,
                    "title": template_data.get("title", ""),
                    "plain_content": template_data.get("plain", ""),
                    "html_content": template_data.get("html", ""),
                    "variables": self.template_manager.get_template_variables(notification_type),
                    "created_at": datetime.now(),  # Заглушка, так как шаблоны статические
                    "updated_at": datetime.now(),
                    "is_active": True,
                    "usage_count": 0  # Заглушка
                })
            
            # Сортируем по типу
            templates_list.sort(key=lambda x: x["type"])
            
            # Применяем пагинацию
            total_count = len(templates_list)
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_templates = templates_list[start_index:end_index]
            
            return paginated_templates, total_count
            
        except Exception as e:
            logger.error(f"Error getting paginated templates: {e}")
            return [], 0

    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Получение шаблона по ID"""
        try:
            # Пытаемся найти шаблон по типу
            try:
                notification_type = NotificationType(template_id)
                template_data = self.template_manager.ALL_TEMPLATES.get(notification_type)
                
                if template_data:
                    return {
                        "id": notification_type.value,
                        "type": notification_type.value,
                        "title": template_data.get("title", ""),
                        "plain_content": template_data.get("plain", ""),
                        "html_content": template_data.get("html", ""),
                        "variables": self.template_manager.get_template_variables(notification_type),
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                        "is_active": True,
                        "usage_count": 0
                    }
            except ValueError:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting template: {e}")
            return None

    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание нового шаблона (заглушка для статических шаблонов)"""
        try:
            # Поскольку шаблоны статические, возвращаем ошибку
            return {
                "status": "error",
                "message": "Создание новых шаблонов пока не поддерживается. Шаблоны являются статическими."
            }
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return {
                "status": "error",
                "message": f"Ошибка создания шаблона: {str(e)}"
            }

    async def update_template(self, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление шаблона (заглушка для статических шаблонов)"""
        try:
            # Поскольку шаблоны статические, возвращаем ошибку
            return {
                "status": "error",
                "message": "Редактирование шаблонов пока не поддерживается. Шаблоны являются статическими."
            }
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return {
                "status": "error",
                "message": f"Ошибка обновления шаблона: {str(e)}"
            }

    async def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Удаление шаблона (заглушка для статических шаблонов)"""
        try:
            # Поскольку шаблоны статические, возвращаем ошибку
            return {
                "status": "error",
                "message": "Удаление шаблонов пока не поддерживается. Шаблоны являются статическими."
            }
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return {
                "status": "error",
                "message": f"Ошибка удаления шаблона: {str(e)}"
            }

    async def test_template(self, template_id: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Тестирование шаблона с тестовыми данными"""
        try:
            # Получаем шаблон
            template = await self.get_template(template_id)
            if not template:
                return {
                    "status": "error",
                    "message": "Шаблон не найден"
                }
            
            # Пытаемся найти тип уведомления
            try:
                notification_type = NotificationType(template_id)
                channel = NotificationChannel.EMAIL  # По умолчанию используем EMAIL для тестирования
                
                # Рендерим шаблон с тестовыми данными
                rendered = self.template_manager.render(notification_type, channel, test_data)
                
                return {
                    "status": "success",
                    "message": "Шаблон успешно протестирован",
                    "result": {
                        "title": rendered.get("title", ""),
                        "message": rendered.get("message", ""),
                        "variables_used": list(test_data.keys()),
                        "variables_missing": self._get_missing_variables(notification_type, test_data)
                    }
                }
                
            except ValueError:
                return {
                    "status": "error",
                    "message": "Неверный тип уведомления"
                }
                
        except Exception as e:
            logger.error(f"Error testing template: {e}")
            return {
                "status": "error",
                "message": f"Ошибка тестирования шаблона: {str(e)}"
            }

    async def get_available_types(self) -> List[Dict[str, str]]:
        """Получение доступных типов уведомлений"""
        try:
            types = []
            for notification_type in NotificationType:
                types.append({
                    "value": notification_type.value,
                    "label": notification_type.value.replace("_", " ").title()
                })
            return types
        except Exception as e:
            logger.error(f"Error getting available types: {e}")
            return []

    async def get_available_channels(self) -> List[Dict[str, str]]:
        """Получение доступных каналов доставки"""
        try:
            channels = []
            for channel in NotificationChannel:
                channels.append({
                    "value": channel.value,
                    "label": channel.value.replace("_", " ").title()
                })
            return channels
        except Exception as e:
            logger.error(f"Error getting available channels: {e}")
            return []

    def _get_missing_variables(self, notification_type: NotificationType, provided_variables: Dict[str, Any]) -> List[str]:
        """Получение списка недостающих переменных"""
        try:
            required_variables = self.template_manager.get_template_variables(notification_type)
            provided_keys = set(provided_variables.keys())
            missing = [var for var in required_variables if var not in provided_keys]
            return missing
        except Exception as e:
            logger.error(f"Error getting missing variables: {e}")
            return []

    async def get_template_statistics(self) -> Dict[str, Any]:
        """Получение статистики по шаблонам"""
        try:
            all_templates = self.template_manager.ALL_TEMPLATES
            
            # Подсчитываем статистику
            total_templates = len(all_templates)
            
            # Группируем по категориям
            categories = {
                "shift": 0,
                "contract": 0,
                "review": 0,
                "payment": 0,
                "system": 0
            }
            
            for notification_type in all_templates.keys():
                type_name = notification_type.value.lower()
                if "shift" in type_name:
                    categories["shift"] += 1
                elif "contract" in type_name:
                    categories["contract"] += 1
                elif "review" in type_name or "appeal" in type_name:
                    categories["review"] += 1
                elif "payment" in type_name or "subscription" in type_name or "usage" in type_name:
                    categories["payment"] += 1
                else:
                    categories["system"] += 1
            
            return {
                "total_templates": total_templates,
                "categories": categories,
                "last_updated": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting template statistics: {e}")
            return {
                "total_templates": 0,
                "categories": {},
                "last_updated": datetime.now()
            }

    async def validate_template_content(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация содержимого шаблона"""
        try:
            errors = []
            warnings = []
            
            # Проверяем обязательные поля
            if not template_data.get("title"):
                errors.append("Заголовок шаблона обязателен")
            
            if not template_data.get("plain_content") and not template_data.get("html_content"):
                errors.append("Необходимо указать содержимое шаблона (plain или html)")
            
            # Проверяем длину заголовка
            title = template_data.get("title", "")
            if len(title) > 200:
                warnings.append("Заголовок слишком длинный (более 200 символов)")
            
            # Проверяем длину содержимого
            plain_content = template_data.get("plain_content", "")
            if len(plain_content) > 2000:
                warnings.append("Текстовое содержимое слишком длинное (более 2000 символов)")
            
            html_content = template_data.get("html_content", "")
            if len(html_content) > 5000:
                warnings.append("HTML содержимое слишком длинное (более 5000 символов)")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating template content: {e}")
            return {
                "valid": False,
                "errors": [f"Ошибка валидации: {str(e)}"],
                "warnings": []
            }

