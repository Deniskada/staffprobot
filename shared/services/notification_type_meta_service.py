"""
Сервис управления мета-информацией типов уведомлений.
Iteration 37: Notification System Overhaul
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.notification_type_meta import NotificationTypeMeta
from core.logging.logger import logger


class NotificationTypeMetaService:
    """Сервис для работы с мета-информацией типов уведомлений"""
    
    async def get_all_types(
        self,
        session: AsyncSession,
        active_only: bool = True
    ) -> List[NotificationTypeMeta]:
        """
        Получить все типы уведомлений.
        
        Args:
            session: Сессия БД
            active_only: Только активные типы
            
        Returns:
            Список объектов NotificationTypeMeta
        """
        query = select(NotificationTypeMeta).order_by(NotificationTypeMeta.sort_order)
        
        if active_only:
            query = query.where(NotificationTypeMeta.is_active == True)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_user_configurable_types(
        self,
        session: AsyncSession,
        active_only: bool = True
    ) -> List[NotificationTypeMeta]:
        """
        Получить типы, доступные для настройки пользователями (владельцами).
        
        Args:
            session: Сессия БД
            active_only: Только активные типы
            
        Returns:
            Список типов с is_user_configurable=True
        """
        query = select(NotificationTypeMeta).where(
            NotificationTypeMeta.is_user_configurable == True
        ).order_by(NotificationTypeMeta.sort_order)
        
        if active_only:
            query = query.where(NotificationTypeMeta.is_active == True)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_types_by_category(
        self,
        session: AsyncSession,
        category: str,
        active_only: bool = True
    ) -> List[NotificationTypeMeta]:
        """
        Получить типы по категории.
        
        Args:
            session: Сессия БД
            category: Категория (shifts, contracts, reviews, payments, system, tasks, applications)
            active_only: Только активные типы
            
        Returns:
            Список типов указанной категории
        """
        query = select(NotificationTypeMeta).where(
            NotificationTypeMeta.category == category
        ).order_by(NotificationTypeMeta.sort_order)
        
        if active_only:
            query = query.where(NotificationTypeMeta.is_active == True)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_types_grouped_by_category(
        self,
        session: AsyncSession,
        user_configurable_only: bool = False,
        active_only: bool = True
    ) -> Dict[str, List[NotificationTypeMeta]]:
        """
        Получить типы сгруппированные по категориям.
        
        Args:
            session: Сессия БД
            user_configurable_only: Только типы для настройки пользователями
            active_only: Только активные типы
            
        Returns:
            Словарь {category: [types]}
        """
        query = select(NotificationTypeMeta).order_by(
            NotificationTypeMeta.category,
            NotificationTypeMeta.sort_order
        )
        
        if user_configurable_only:
            query = query.where(NotificationTypeMeta.is_user_configurable == True)
        
        if active_only:
            query = query.where(NotificationTypeMeta.is_active == True)
        
        result = await session.execute(query)
        types = result.scalars().all()
        
        # Группировка по категориям
        grouped = {}
        for type_obj in types:
            if type_obj.category not in grouped:
                grouped[type_obj.category] = []
            grouped[type_obj.category].append(type_obj)
        
        return grouped
    
    async def get_type_by_code(
        self,
        session: AsyncSession,
        type_code: str
    ) -> Optional[NotificationTypeMeta]:
        """
        Получить тип по коду.
        
        Args:
            session: Сессия БД
            type_code: Код типа
            
        Returns:
            Объект NotificationTypeMeta или None
        """
        result = await session.execute(
            select(NotificationTypeMeta).where(
                NotificationTypeMeta.type_code == type_code
            )
        )
        return result.scalar_one_or_none()
    
    async def activate_type(
        self,
        session: AsyncSession,
        type_code: str,
        is_user_configurable: bool = False
    ) -> bool:
        """
        Активировать тип для использования (сделать доступным для пользователей).
        
        Args:
            session: Сессия БД
            type_code: Код типа
            is_user_configurable: Сделать доступным для настройки владельцами
            
        Returns:
            True если успешно, False если тип не найден
        """
        type_obj = await self.get_type_by_code(session, type_code)
        if not type_obj:
            logger.warning(f"Type {type_code} not found for activation")
            return False
        
        type_obj.is_active = True
        if is_user_configurable:
            type_obj.is_user_configurable = is_user_configurable
        
        await session.commit()
        logger.info(f"Type {type_code} activated, user_configurable={is_user_configurable}")
        return True
    
    async def deactivate_type(
        self,
        session: AsyncSession,
        type_code: str
    ) -> bool:
        """
        Деактивировать тип (убрать из настроек пользователей).
        
        Args:
            session: Сессия БД
            type_code: Код типа
            
        Returns:
            True если успешно, False если тип не найден
        """
        type_obj = await self.get_type_by_code(session, type_code)
        if not type_obj:
            logger.warning(f"Type {type_code} not found for deactivation")
            return False
        
        type_obj.is_active = False
        type_obj.is_user_configurable = False
        
        await session.commit()
        logger.info(f"Type {type_code} deactivated")
        return True
    
    async def update_type(
        self,
        session: AsyncSession,
        type_code: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        default_priority: Optional[str] = None,
        available_channels: Optional[List[str]] = None,
        sort_order: Optional[int] = None
    ) -> Optional[NotificationTypeMeta]:
        """
        Обновить мета-информацию типа.
        
        Args:
            session: Сессия БД
            type_code: Код типа
            title: Новое название
            description: Новое описание
            default_priority: Новый приоритет
            available_channels: Новые доступные каналы
            sort_order: Новый порядок сортировки
            
        Returns:
            Обновлённый объект или None
        """
        type_obj = await self.get_type_by_code(session, type_code)
        if not type_obj:
            logger.warning(f"Type {type_code} not found for update")
            return None
        
        if title is not None:
            type_obj.title = title
        if description is not None:
            type_obj.description = description
        if default_priority is not None:
            type_obj.default_priority = default_priority
        if available_channels is not None:
            type_obj.available_channels = available_channels
        if sort_order is not None:
            type_obj.sort_order = sort_order
        
        await session.commit()
        logger.info(f"Type {type_code} updated")
        return type_obj
    
    async def get_categories_list(
        self,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Получить список категорий с количеством типов в каждой.
        
        Args:
            session: Сессия БД
            
        Returns:
            Список словарей с информацией о категориях
        """
        # Названия категорий на русском
        category_names = {
            "shifts": "Смены",
            "contracts": "Договоры",
            "reviews": "Отзывы",
            "payments": "Платежи",
            "system": "Системные",
            "tasks": "Задачи",
            "applications": "Заявки"
        }
        
        # Подсчёт типов по категориям
        result = await session.execute(
            select(
                NotificationTypeMeta.category,
                func.count(NotificationTypeMeta.id).label('count')
            ).group_by(NotificationTypeMeta.category)
        )
        
        categories = []
        for row in result:
            category_code = row.category
            categories.append({
                "code": category_code,
                "name": category_names.get(category_code, category_code),
                "count": row.count
            })
        
        return sorted(categories, key=lambda x: x['name'])

