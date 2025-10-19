"""
Сервис для работы с функциями системы.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.system_feature import SystemFeature
from domain.entities.user_subscription import UserSubscription
from domain.entities.tariff_plan import TariffPlan
from domain.entities.owner_profile import OwnerProfile
from core.logging.logger import logger


class SystemFeaturesService:
    """Сервис управления функциями системы."""
    
    async def get_all_features(
        self,
        session: AsyncSession,
        active_only: bool = True
    ) -> List[SystemFeature]:
        """Получить все функции системы."""
        
        query = select(SystemFeature).order_by(SystemFeature.sort_order)
        
        if active_only:
            query = query.where(SystemFeature.is_active == True)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_feature_by_key(
        self,
        session: AsyncSession,
        key: str
    ) -> Optional[SystemFeature]:
        """Получить функцию по ключу."""
        
        result = await session.execute(
            select(SystemFeature).where(SystemFeature.key == key)
        )
        return result.scalar_one_or_none()
    
    async def get_available_features_for_tariff(
        self,
        session: AsyncSession,
        tariff_id: int
    ) -> List[str]:
        """Получить ключи функций, доступных в тарифе."""
        
        result = await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_id)
        )
        tariff = result.scalar_one_or_none()
        
        if not tariff or not tariff.features:
            return []
        
        return tariff.features
    
    async def get_user_features_status(
        self,
        session: AsyncSession,
        user_id: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получить статус функций для пользователя.
        
        Returns:
            Dict с ключами функций и их статусом:
            {
                'feature_key': {
                    'available': bool,  # доступна в тарифе
                    'enabled': bool,     # включена пользователем
                    'info': SystemFeature
                }
            }
        """
        
        # Получаем все функции
        all_features = await self.get_all_features(session)
        
        # Получаем текущую подписку пользователя
        result = await session.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .order_by(UserSubscription.created_at.desc())
            .limit(1)
        )
        subscription = result.scalar_one_or_none()
        
        # Получаем функции тарифа
        available_keys = []
        if subscription and subscription.tariff_plan_id:
            available_keys = await self.get_available_features_for_tariff(
                session,
                subscription.tariff_plan_id
            )
        
        # Получаем включенные функции из профиля
        result = await session.execute(
            select(OwnerProfile).where(OwnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        enabled_keys = profile.enabled_features if profile and profile.enabled_features else []
        
        # Формируем статус
        status = {}
        for feature in all_features:
            status[feature.key] = {
                'available': feature.key in available_keys,
                'enabled': feature.key in enabled_keys,
                'info': feature
            }
        
        return status
    
    async def toggle_user_feature(
        self,
        session: AsyncSession,
        user_id: int,
        feature_key: str,
        enabled: bool
    ) -> bool:
        """
        Включить/выключить функцию для пользователя.
        
        Returns:
            True если успешно, False если функция недоступна в тарифе
        """
        
        # Проверяем, доступна ли функция в тарифе
        status = await self.get_user_features_status(session, user_id)
        if feature_key not in status or not status[feature_key]['available']:
            logger.warning(
                f"Feature {feature_key} not available for user {user_id}"
            )
            return False
        
        # Получаем или создаём профиль
        result = await session.execute(
            select(OwnerProfile).where(OwnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            logger.error(f"Owner profile not found for user {user_id}")
            return False
        
        # Обновляем список включенных функций
        enabled_features = profile.enabled_features if profile.enabled_features else []
        
        if enabled:
            if feature_key not in enabled_features:
                enabled_features.append(feature_key)
        else:
            if feature_key in enabled_features:
                enabled_features.remove(feature_key)
        
        profile.enabled_features = enabled_features
        await session.commit()
        
        logger.info(
            f"Toggled feature {feature_key} to {enabled} for user {user_id}"
        )
        return True
    
    async def get_enabled_features(
        self,
        session: AsyncSession,
        user_id: int
    ) -> List[str]:
        """Получить список ключей включенных функций пользователя."""
        
        result = await session.execute(
            select(OwnerProfile).where(OwnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile or not profile.enabled_features:
            return []
        
        return profile.enabled_features
    
    async def is_feature_enabled(
        self,
        session: AsyncSession,
        user_id: int,
        feature_key: str
    ) -> bool:
        """Проверить, включена ли функция для пользователя."""
        
        enabled_features = await self.get_enabled_features(session, user_id)
        return feature_key in enabled_features
    
    async def increment_usage(
        self,
        session: AsyncSession,
        feature_key: str
    ):
        """Увеличить счётчик использования функции."""
        
        feature = await self.get_feature_by_key(session, feature_key)
        if feature:
            feature.increment_usage()
            await session.commit()

