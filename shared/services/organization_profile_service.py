"""
Сервис для работы с профилями организаций (реквизиты ИП/ЮЛ).
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.organization_profile import OrganizationProfile
from core.logging.logger import logger


class OrganizationProfileService:
    """Сервис управления профилями организаций."""
    
    async def create_profile(
        self,
        session: AsyncSession,
        user_id: int,
        profile_name: str,
        legal_type: str,
        requisites: Dict[str, Any],
        is_default: bool = False
    ) -> OrganizationProfile:
        """Создать профиль организации."""
        
        # Если создаётся профиль по умолчанию, сбрасываем флаг у других
        if is_default:
            await self._reset_default_flag(session, user_id)
        
        profile = OrganizationProfile(
            user_id=user_id,
            profile_name=profile_name,
            legal_type=legal_type,
            requisites=requisites,
            is_default=is_default
        )
        
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        
        logger.info(f"Created organization profile: {profile_name} for user {user_id}")
        return profile
    
    async def update_profile(
        self,
        session: AsyncSession,
        profile_id: int,
        data: Dict[str, Any]
    ) -> Optional[OrganizationProfile]:
        """Обновить профиль организации."""
        
        result = await session.execute(
            select(OrganizationProfile).where(OrganizationProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return None
        
        # Если устанавливается is_default, сбрасываем у других
        if data.get('is_default') and not profile.is_default:
            await self._reset_default_flag(session, profile.user_id)
        
        # Обновляем поля
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        await session.commit()
        await session.refresh(profile)
        
        logger.info(f"Updated organization profile: {profile.id}")
        return profile
    
    async def delete_profile(
        self,
        session: AsyncSession,
        profile_id: int
    ) -> bool:
        """Удалить профиль организации."""
        
        result = await session.execute(
            select(OrganizationProfile).where(OrganizationProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return False
        
        await session.delete(profile)
        await session.commit()
        
        logger.info(f"Deleted organization profile: {profile_id}")
        return True
    
    async def list_user_profiles(
        self,
        session: AsyncSession,
        user_id: int
    ) -> List[OrganizationProfile]:
        """Получить список профилей пользователя."""
        
        result = await session.execute(
            select(OrganizationProfile)
            .where(OrganizationProfile.user_id == user_id)
            .order_by(OrganizationProfile.is_default.desc(), OrganizationProfile.created_at)
        )
        return list(result.scalars().all())
    
    async def get_profile(
        self,
        session: AsyncSession,
        profile_id: int
    ) -> Optional[OrganizationProfile]:
        """Получить профиль по ID."""
        
        result = await session.execute(
            select(OrganizationProfile).where(OrganizationProfile.id == profile_id)
        )
        return result.scalar_one_or_none()
    
    async def get_default_profile(
        self,
        session: AsyncSession,
        user_id: int
    ) -> Optional[OrganizationProfile]:
        """Получить профиль по умолчанию."""
        
        result = await session.execute(
            select(OrganizationProfile)
            .where(
                OrganizationProfile.user_id == user_id,
                OrganizationProfile.is_default == True
            )
        )
        profile = result.scalar_one_or_none()
        
        # Если нет профиля по умолчанию, возвращаем первый
        if not profile:
            result = await session.execute(
                select(OrganizationProfile)
                .where(OrganizationProfile.user_id == user_id)
                .order_by(OrganizationProfile.created_at)
                .limit(1)
            )
            profile = result.scalar_one_or_none()
        
        return profile
    
    async def set_default_profile(
        self,
        session: AsyncSession,
        profile_id: int
    ) -> bool:
        """Установить профиль как профиль по умолчанию."""
        
        result = await session.execute(
            select(OrganizationProfile).where(OrganizationProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return False
        
        # Сбрасываем флаг у других профилей пользователя
        await self._reset_default_flag(session, profile.user_id)
        
        # Устанавливаем флаг для текущего
        profile.is_default = True
        await session.commit()
        
        logger.info(f"Set default organization profile: {profile_id}")
        return True
    
    async def get_profile_tags_for_templates(
        self,
        session: AsyncSession,
        profile_id: int
    ) -> Dict[str, Any]:
        """Получить теги профиля для подстановки в шаблоны."""
        
        profile = await self.get_profile(session, profile_id)
        if not profile:
            return {}
        
        return profile.get_tags_for_templates()
    
    async def _reset_default_flag(
        self,
        session: AsyncSession,
        user_id: int
    ):
        """Сбросить флаг is_default у всех профилей пользователя."""
        
        result = await session.execute(
            select(OrganizationProfile)
            .where(
                OrganizationProfile.user_id == user_id,
                OrganizationProfile.is_default == True
            )
        )
        profiles = result.scalars().all()
        
        for profile in profiles:
            profile.is_default = False

