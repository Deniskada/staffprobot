"""Сервис для управления шаблонами уведомлений через веб-интерфейс.
Iteration 25, Phase 3: CRUD для кастомных шаблонов
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import json
from sqlalchemy import select, func, and_, desc, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.notification import NotificationType, NotificationChannel
from domain.entities.notification_template import NotificationTemplate
from shared.templates.notifications.base_templates import NotificationTemplateManager
from core.logging.logger import logger


class NotificationTemplateService:
    """Сервис для управления шаблонами уведомлений через веб-интерфейс
    
    Логика работы:
    1. Статические шаблоны из shared/templates/notifications/ - базовые
    2. Кастомные шаблоны из БД (NotificationTemplate) - переопределяют статические
    3. При рендеринге: сначала ищем кастомные, затем статические
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.template_manager = NotificationTemplateManager()

    # ========================================================================
    # МЕТОДЫ CRUD ДЛЯ КАСТОМНЫХ ШАБЛОНОВ
    # ========================================================================

    async def create_template(
        self,
        template_key: str,
        notification_type: NotificationType,
        channel: Optional[NotificationChannel],
        name: str,
        plain_template: str,
        subject_template: Optional[str] = None,
        html_template: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[List[str]] = None,
        created_by_user_id: Optional[int] = None
    ) -> NotificationTemplate:
        """Создание нового кастомного шаблона"""
        try:
            # Проверяем, нет ли уже такого ключа
            existing = await self.get_template_by_key(template_key)
            if existing:
                raise ValueError(f"Шаблон с ключом '{template_key}' уже существует")

            # Создаём новый шаблон
            template = NotificationTemplate(
                template_key=template_key,
                type=notification_type,
                channel=channel,
                name=name,
                description=description,
                subject_template=subject_template,
                plain_template=plain_template,
                html_template=html_template,
                variables=json.dumps(variables) if variables else None,
                is_active=True,
                is_default=False,
                created_by=created_by_user_id,
                version=1
            )

            self.session.add(template)
            await self.session.commit()
            await self.session.refresh(template)

            logger.info(f"Created custom template: {template_key} (ID: {template.id})")
            return template

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating template: {e}")
            raise

    async def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        plain_template: Optional[str] = None,
        subject_template: Optional[str] = None,
        html_template: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        updated_by_user_id: Optional[int] = None
    ) -> NotificationTemplate:
        """Обновление существующего шаблона"""
        try:
            # Получаем шаблон
            template = await self.get_template_by_id(template_id)
            if not template:
                raise ValueError(f"Шаблон с ID {template_id} не найден")

            # Обновляем поля
            if name is not None:
                template.name = name
            if plain_template is not None:
                template.plain_template = plain_template
            if subject_template is not None:
                template.subject_template = subject_template
            if html_template is not None:
                template.html_template = html_template
            if description is not None:
                template.description = description
            if variables is not None:
                template.variables = json.dumps(variables)
            if is_active is not None:
                template.is_active = is_active
            if updated_by_user_id is not None:
                template.updated_by = updated_by_user_id

            # Увеличиваем версию
            template.version += 1

            await self.session.commit()
            await self.session.refresh(template)

            logger.info(f"Updated template ID {template_id} to version {template.version}")
            return template

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating template: {e}")
            raise

    async def delete_template(self, template_id: int) -> None:
        """Удаление шаблона (мягкое удаление - деактивация)"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                raise ValueError(f"Шаблон с ID {template_id} не найден")

            # Не удаляем дефолтные шаблоны
            if template.is_default:
                raise ValueError("Нельзя удалить дефолтный шаблон")

            # Деактивируем вместо удаления
            template.is_active = False
            await self.session.commit()

            logger.info(f"Deactivated template ID {template_id}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting template: {e}")
            raise

    async def hard_delete_template(self, template_id: int) -> None:
        """Жёсткое удаление шаблона из БД"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                raise ValueError(f"Шаблон с ID {template_id} не найден")

            # Не удаляем дефолтные шаблоны
            if template.is_default:
                raise ValueError("Нельзя удалить дефолтный шаблон")

            await self.session.delete(template)
            await self.session.commit()

            logger.info(f"Hard deleted template ID {template_id}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error hard deleting template: {e}")
            raise

    # ========================================================================
    # МЕТОДЫ ПОЛУЧЕНИЯ ШАБЛОНОВ
    # ========================================================================

    async def get_template_by_id(self, template_id: int) -> Optional[NotificationTemplate]:
        """Получение шаблона по ID"""
        try:
            query = select(NotificationTemplate).where(NotificationTemplate.id == template_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting template by ID: {e}")
            return None

    async def get_template_by_key(self, template_key: str) -> Optional[NotificationTemplate]:
        """Получение шаблона по ключу"""
        try:
            query = select(NotificationTemplate).where(NotificationTemplate.template_key == template_key)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting template by key: {e}")
            return None

    async def get_templates_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        type_filter: Optional[str] = None,
        channel_filter: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> Tuple[List[NotificationTemplate], int]:
        """Получение кастомных шаблонов с пагинацией и фильтрами"""
        try:
            # Базовый запрос
            query = select(NotificationTemplate)

            # Применяем фильтры
            filters = []

            if type_filter:
                try:
                    notification_type = NotificationType(type_filter)
                    filters.append(NotificationTemplate.type == notification_type)
                except ValueError:
                    pass

            if channel_filter:
                try:
                    channel = NotificationChannel(channel_filter)
                    filters.append(NotificationTemplate.channel == channel)
                except ValueError:
                    pass

            if is_active is not None:
                filters.append(NotificationTemplate.is_active == is_active)

            if search_query:
                filters.append(
                    NotificationTemplate.name.ilike(f"%{search_query}%") |
                    NotificationTemplate.description.ilike(f"%{search_query}%") |
                    NotificationTemplate.template_key.ilike(f"%{search_query}%")
                )

            if filters:
                query = query.where(and_(*filters))

            # Подсчитываем общее количество
            count_query = select(func.count()).select_from(query.subquery())
            total_count = await self.session.scalar(count_query)

            # Применяем сортировку и пагинацию
            query = query.order_by(desc(NotificationTemplate.created_at))
            query = query.offset((page - 1) * per_page).limit(per_page)

            # Выполняем запрос
            result = await self.session.execute(query)
            templates = result.scalars().all()

            return list(templates), total_count or 0

        except Exception as e:
            logger.error(f"Error getting paginated templates: {e}")
            return [], 0

    async def get_all_templates_merged(
        self,
        notification_type: Optional[NotificationType] = None
    ) -> Dict[str, Any]:
        """Получение всех шаблонов (кастомные + статические), кастомные имеют приоритет"""
        try:
            # Получаем статические шаблоны
            static_templates = {}
            for ntype, template_data in self.template_manager.ALL_TEMPLATES.items():
                if notification_type is None or ntype == notification_type:
                    static_templates[ntype.value] = {
                        "source": "static",
                        "type": ntype.value,
                        "title": template_data.get("title", ""),
                        "plain": template_data.get("plain", ""),
                        "html": template_data.get("html", ""),
                        "variables": self.template_manager.get_template_variables(ntype)
                    }

            # Получаем кастомные шаблоны
            query = select(NotificationTemplate).where(NotificationTemplate.is_active == True)
            if notification_type:
                query = query.where(NotificationTemplate.type == notification_type)

            result = await self.session.execute(query)
            custom_templates = result.scalars().all()

            # Переопределяем статические кастомными
            for template in custom_templates:
                key = template.type.value
                static_templates[key] = {
                    "source": "custom",
                    "id": template.id,
                    "template_key": template.template_key,
                    "type": template.type.value,
                    "channel": template.channel.value if template.channel else None,
                    "name": template.name,
                    "description": template.description,
                    "subject": template.subject_template,
                    "plain": template.plain_template,
                    "html": template.html_template,
                    "variables": json.loads(template.variables) if template.variables else [],
                    "is_active": template.is_active,
                    "version": template.version,
                    "created_at": template.created_at.isoformat() if template.created_at else None,
                    "updated_at": template.updated_at.isoformat() if template.updated_at else None
                }

            return static_templates

        except Exception as e:
            logger.error(f"Error getting merged templates: {e}")
            return {}

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================

    async def get_available_types(self) -> List[Dict[str, str]]:
        """Получение доступных типов уведомлений"""
        try:
            types = []
            for notification_type in NotificationType:
                # Преобразуем enum в строку безопасно
                value = notification_type.value if isinstance(notification_type.value, str) else str(notification_type.value)
                types.append({
                    "value": value,
                    "label": value.replace("_", " ").title()
                })
            return types
        except Exception as e:
            logger.error(f"Error getting available types: {e}", exc_info=True)
            return []

    async def get_available_channels(self) -> List[Dict[str, str]]:
        """Получение доступных каналов доставки"""
        try:
            channels = []
            for channel in NotificationChannel:
                # Преобразуем enum в строку безопасно
                value = channel.value if isinstance(channel.value, str) else str(channel.value)
                channels.append({
                    "value": value,
                    "label": value.replace("_", " ").title()
                })
            return channels
        except Exception as e:
            logger.error(f"Error getting available channels: {e}", exc_info=True)
            return []

    async def get_template_statistics(self) -> Dict[str, Any]:
        """Получение статистики по шаблонам"""
        try:
            # Статические шаблоны
            static_count = len(self.template_manager.ALL_TEMPLATES)

            # Кастомные шаблоны
            custom_count_query = select(func.count()).select_from(NotificationTemplate)
            custom_count = await self.session.scalar(custom_count_query) or 0

            # Активные кастомные
            active_custom_query = select(func.count()).select_from(NotificationTemplate).where(
                NotificationTemplate.is_active == True
            )
            active_custom_count = await self.session.scalar(active_custom_query) or 0

            return {
                "total_static": static_count,
                "total_custom": custom_count,
                "active_custom": active_custom_count,
                "last_updated": datetime.now()
            }

        except Exception as e:
            logger.error(f"Error getting template statistics: {e}")
            return {
                "total_static": 0,
                "total_custom": 0,
                "active_custom": 0,
                "last_updated": datetime.now()
            }

    def _get_missing_variables(
        self,
        notification_type: NotificationType,
        provided_variables: Dict[str, Any]
    ) -> List[str]:
        """Получение списка недостающих переменных"""
        try:
            required_variables = self.template_manager.get_template_variables(notification_type)
            provided_keys = set(provided_variables.keys())
            missing = [var for var in required_variables if var not in provided_keys]
            return missing
        except Exception as e:
            logger.error(f"Error getting missing variables: {e}")
            return []
