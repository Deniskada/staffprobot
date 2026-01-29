"""Абстрактный KYC‑слой для профилей (через провайдеров)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging.logger import logger
from domain.entities.profile import Profile, KycStatus


class KycProvider:
    """Базовый интерфейс провайдера KYC.

    На этом этапе реализуем простой провайдер-заглушку для госуслуг.
    """

    provider_key: str = "gosuslugi"

    async def start_verification(self, profile: Profile) -> Dict[str, Any]:
        """
        Инициация верификации.

        Возвращает payload с данными для фронта (например, redirect_url).
        Сейчас возвращаем заглушку, реальная интеграция добавится позже.
        """
        # В реальной интеграции здесь формируется redirect_url на ЕСИА/госуслуги.
        return {
            "provider": self.provider_key,
            "redirect_url": None,
        }

    async def complete_verification(self, profile: Profile, payload: Dict[str, Any]) -> bool:
        """
        Завершение верификации.

        payload — данные от callback'а провайдера.
        Сейчас просто помечаем профиль как верифицированный.
        """
        return True


class GosuslugiKycProvider(KycProvider):
    """Провайдер KYC для госуслуг (заглушка)."""

    provider_key = "gosuslugi"


class KycService:
    """Сервис оркестрации KYC‑потока для профилей."""

    def __init__(self, provider: Optional[KycProvider] = None) -> None:
        self.provider = provider or GosuslugiKycProvider()

    async def _get_profile(self, session: AsyncSession, profile_id: int, user_id: int) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def start_verification(self, session: AsyncSession, profile_id: int, user_id: int) -> Dict[str, Any]:
        """Перевести профиль в статус PENDING и вернуть данные для начала KYC‑процесса."""
        profile = await self._get_profile(session, profile_id, user_id)
        if not profile:
            raise ValueError("Профиль не найден")

        profile.kyc_status = KycStatus.PENDING.value
        profile.kyc_provider = self.provider.provider_key
        await session.flush()

        provider_payload = await self.provider.start_verification(profile)
        profile.kyc_metadata = provider_payload

        await session.commit()
        logger.info("KYC started", profile_id=profile.id, user_id=user_id, provider=profile.kyc_provider)
        return {
            "status": profile.kyc_status,
            "provider": profile.kyc_provider,
            "redirect_url": provider_payload.get("redirect_url"),
        }

    async def mark_verified(
        self,
        session: AsyncSession,
        profile_id: int,
        user_id: int,
        provider_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Пометить профиль как верифицированный.

        На этом этапе вызывается напрямую после успешного прохождения KYC‑потока
        (вместо полноценного callback'а от провайдера).
        """
        profile = await self._get_profile(session, profile_id, user_id)
        if not profile:
            raise ValueError("Профиль не найден")

        profile.kyc_status = KycStatus.VERIFIED.value
        profile.kyc_verified_at = datetime.now(timezone.utc)
        profile.kyc_provider = self.provider.provider_key

        if provider_payload:
            existing_meta = profile.kyc_metadata or {}
            merged = {**existing_meta, **provider_payload}
            profile.kyc_metadata = merged

        await session.commit()
        logger.info("KYC verified", profile_id=profile.id, user_id=user_id, provider=profile.kyc_provider)

        return {
            "status": profile.kyc_status,
            "verified_at": profile.kyc_verified_at.isoformat() if profile.kyc_verified_at else None,
        }

    async def mark_failed(
        self,
        session: AsyncSession,
        profile_id: int,
        user_id: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Пометить профиль как не прошедший KYC."""
        profile = await self._get_profile(session, profile_id, user_id)
        if not profile:
            raise ValueError("Профиль не найден")

        profile.kyc_status = KycStatus.FAILED.value

        if reason:
            existing_meta = profile.kyc_metadata or {}
            existing_meta["last_error"] = reason
            profile.kyc_metadata = existing_meta

        await session.commit()
        logger.info("KYC failed", profile_id=profile.id, user_id=user_id, reason=reason)
        return {
            "status": profile.kyc_status,
            "error": reason,
        }

