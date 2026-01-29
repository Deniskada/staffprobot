"""Сервис для работы с пользовательскими профилями (ФЛ, ИП, ЮЛ)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging.logger import logger
from domain.entities.profile import (
    Profile,
    ProfileType,
    IndividualProfile,
    LegalProfile,
    SoleProprietorProfile,
)
from domain.entities.address import Address


class ProfileService:
    """Бизнес‑логика для CRUD операций над профилями пользователя."""

    @staticmethod
    def _parse_iso_date(value: Any) -> Optional[datetime]:
        """
        Преобразовать значение из формы (строка YYYY-MM-DD) в datetime.
        Если парсинг не удался, вернуть None, чтобы не ломать сохранение.
        """
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        if isinstance(value, str):
            try:
                # Поддерживаем как дату, так и полную дату-время
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    async def list_user_profiles(self, session: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
        """Вернуть список профилей пользователя в виде DTO для API."""
        stmt = (
            select(Profile)
            .where(Profile.user_id == user_id, Profile.is_archived.is_(False))
            .order_by(Profile.is_default.desc(), Profile.created_at)
        )
        result = await session.execute(stmt)
        profiles: List[Profile] = list(result.scalars().all())

        return [await self._profile_to_dto(session, p) for p in profiles]

    async def get_profile_dto(self, session: AsyncSession, profile_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить один профиль (с проверкой владельца)."""
        stmt = select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
        result = await session.execute(stmt)
        profile: Optional[Profile] = result.scalar_one_or_none()
        if not profile:
            return None
        return await self._profile_to_dto(session, profile)

    async def create_profile(
        self,
        session: AsyncSession,
        user_id: int,
        base_data: Dict[str, Any],
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Создать профиль и типоспецифичную запись."""
        profile_type = ProfileType(base_data["profile_type"])

        if base_data.get("is_default"):
            await self._reset_default_flag(session, user_id)

        profile = Profile(
            user_id=user_id,
            profile_type=profile_type.value,
            display_name=base_data["display_name"],
            is_default=bool(base_data.get("is_default")),
        )
        session.add(profile)
        await session.flush()  # чтобы получить profile.id

        await self._upsert_details(session, profile, details, is_create=True)

        await session.commit()
        await session.refresh(profile)

        logger.info("Profile created", user_id=user_id, profile_id=profile.id, profile_type=profile.profile_type)
        return await self._profile_to_dto(session, profile)

    async def update_profile(
        self,
        session: AsyncSession,
        profile_id: int,
        user_id: int,
        base_data: Dict[str, Any],
        details: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Обновить базовый профиль и его детали."""
        stmt = select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
        result = await session.execute(stmt)
        profile: Optional[Profile] = result.scalar_one_or_none()
        if not profile:
            return None

        # Обновляем базовые поля
        if "display_name" in base_data:
            profile.display_name = base_data["display_name"]

        new_type = base_data.get("profile_type")
        if new_type and new_type != profile.profile_type:
            profile.profile_type = new_type
            # При смене типа детали будут пересозданы

        if base_data.get("is_default") and not profile.is_default:
            await self._reset_default_flag(session, user_id)
            profile.is_default = True
        elif "is_default" in base_data and not base_data.get("is_default"):
            profile.is_default = False

        await self._upsert_details(session, profile, details, is_create=False)

        await session.commit()
        await session.refresh(profile)

        logger.info("Profile updated", user_id=user_id, profile_id=profile.id, profile_type=profile.profile_type)
        return await self._profile_to_dto(session, profile)

    async def delete_profile(self, session: AsyncSession, profile_id: int, user_id: int) -> bool:
        """Архивировать профиль (мягкое удаление)."""
        stmt = select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
        result = await session.execute(stmt)
        profile: Optional[Profile] = result.scalar_one_or_none()
        if not profile:
            return False

        profile.is_archived = True
        await session.commit()

        logger.info("Profile archived", user_id=user_id, profile_id=profile.id)
        return True

    async def set_default_profile(self, session: AsyncSession, profile_id: int, user_id: int) -> bool:
        """Сделать профиль профилем по умолчанию."""
        stmt = select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
        result = await session.execute(stmt)
        profile: Optional[Profile] = result.scalar_one_or_none()
        if not profile:
            return False

        await self._reset_default_flag(session, user_id)
        profile.is_default = True
        await session.commit()

        logger.info("Profile set as default", user_id=user_id, profile_id=profile.id)
        return True

    async def _reset_default_flag(self, session: AsyncSession, user_id: int) -> None:
        stmt = select(Profile).where(Profile.user_id == user_id, Profile.is_default.is_(True))
        result = await session.execute(stmt)
        profiles = result.scalars().all()
        for p in profiles:
            p.is_default = False

    async def _profile_to_dto(self, session: AsyncSession, profile: Profile) -> Dict[str, Any]:
        """Преобразовать профиль и связанные данные в DTO."""
        base = {
            "id": profile.id,
            "user_id": profile.user_id,
            "profile_type": profile.profile_type,
            "display_name": profile.display_name,
            "is_default": profile.is_default,
            "is_archived": profile.is_archived,
            "kyc_status": profile.kyc_status,
            "kyc_provider": profile.kyc_provider,
            "kyc_verified_at": profile.kyc_verified_at.isoformat() if profile.kyc_verified_at else None,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

        details: Dict[str, Any]
        if profile.profile_type == ProfileType.INDIVIDUAL.value:
            details = await self._individual_details_to_dict(session, profile.id)
        elif profile.profile_type == ProfileType.LEGAL.value:
            details = await self._legal_details_to_dict(session, profile.id)
        else:
            details = await self._sp_details_to_dict(session, profile.id)

        base["details"] = details
        base["is_verified"] = profile.kyc_status == "verified"
        return base

    async def _load_details(
        self,
        session: AsyncSession,
        model,
        profile_id: int,
    ) -> Optional[Any]:
        stmt = select(model).where(model.profile_id == profile_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _upsert_details(
        self,
        session: AsyncSession,
        profile: Profile,
        details: Dict[str, Any],
        is_create: bool,
    ) -> None:
        """Создать или обновить запись с деталями профиля."""
        profile_type = ProfileType(profile.profile_type)

        if profile_type is ProfileType.INDIVIDUAL:
            instance = await self._load_details(session, IndividualProfile, profile.id)
            if not instance:
                instance = IndividualProfile(profile_id=profile.id)
                session.add(instance)
            self._apply_individual_details(instance, details)
        elif profile_type is ProfileType.LEGAL:
            instance = await self._load_details(session, LegalProfile, profile.id)
            if not instance:
                instance = LegalProfile(profile_id=profile.id)
                session.add(instance)
            # Преобразуем profile_id в individual_profiles.id для representative_profile_id
            if "representative_profile_id" in details:
                rep_profile_id = details.get("representative_profile_id")
                if rep_profile_id:
                    try:
                        rep_profile_id_int = int(rep_profile_id) if rep_profile_id != "" else None
                        if rep_profile_id_int:
                            # Ищем individual_profiles.id по profile_id
                            stmt = select(IndividualProfile.id).where(IndividualProfile.profile_id == rep_profile_id_int)
                            result = await session.execute(stmt)
                            individual_profile_id = result.scalar_one_or_none()
                            if individual_profile_id:
                                details["representative_profile_id"] = individual_profile_id
                            else:
                                # Если не найден individual_profile, очищаем значение
                                details["representative_profile_id"] = None
                                logger.warning(
                                    "Representative profile not found or not individual",
                                    profile_id=rep_profile_id_int,
                                )
                        else:
                            details["representative_profile_id"] = None
                    except (TypeError, ValueError):
                        details["representative_profile_id"] = None
                else:
                    details["representative_profile_id"] = None
            self._apply_legal_details(instance, details)
        else:
            instance = await self._load_details(session, SoleProprietorProfile, profile.id)
            if not instance:
                instance = SoleProprietorProfile(profile_id=profile.id)
                session.add(instance)
            self._apply_sp_details(instance, details)

    def _apply_individual_details(self, entity: IndividualProfile, data: Dict[str, Any]) -> None:
        # Гражданство, личные данные
        entity.citizenship = data.get("citizenship") or entity.citizenship
        entity.last_name = data.get("last_name") or entity.last_name
        entity.first_name = data.get("first_name") or entity.first_name
        entity.middle_name = data.get("middle_name") or entity.middle_name
        entity.gender = data.get("gender") or entity.gender
        entity.is_self_employed = bool(data.get("is_self_employed", entity.is_self_employed))

        raw_birth = data.get("birth_date")
        parsed_birth = self._parse_iso_date(raw_birth)
        if parsed_birth is not None:
            entity.birth_date = parsed_birth

        # Паспорт
        entity.passport_series = data.get("passport_series") or entity.passport_series
        entity.passport_number = data.get("passport_number") or entity.passport_number
        raw_issued = data.get("passport_issued_at")
        parsed_issued = self._parse_iso_date(raw_issued)
        if parsed_issued is not None:
            entity.passport_issued_at = parsed_issued
        entity.passport_issued_by = data.get("passport_issued_by") or entity.passport_issued_by
        entity.passport_department_code = data.get("passport_department_code") or entity.passport_department_code
        if "registration_address_id" in data:
            raw_reg_id = data.get("registration_address_id")
            try:
                entity.registration_address_id = int(raw_reg_id) if raw_reg_id is not None else None
            except (TypeError, ValueError):
                entity.registration_address_id = None
        if "residence_address_id" in data:
            # может совпадать с адресом регистрации или быть отдельным
            raw_res_id = data.get("residence_address_id")
            try:
                entity.residence_address_id = int(raw_res_id) if raw_res_id is not None else None
            except (TypeError, ValueError):
                entity.residence_address_id = None

        # Регистрационные данные
        entity.snils = data.get("snils") or entity.snils
        entity.inn = data.get("inn") or entity.inn

        # Контакты и банк
        entity.phone = data.get("phone") or entity.phone
        entity.email = data.get("email") or entity.email
        entity.max_contact = data.get("max_contact") or entity.max_contact

        entity.account_number = data.get("account_number") or entity.account_number
        entity.correspondent_account = data.get("correspondent_account") or entity.correspondent_account
        entity.bank_name = data.get("bank_name") or entity.bank_name
        entity.bik = data.get("bik") or entity.bik

    def _apply_legal_details(self, entity: LegalProfile, data: Dict[str, Any]) -> None:
        entity.full_name = data.get("full_name") or entity.full_name
        entity.ogrn = data.get("ogrn") or entity.ogrn
        # Дата присвоения ОГРН - всегда обрабатываем, даже если пустая
        if "ogrn_assigned_at" in data:
            raw_ogrn_date = data.get("ogrn_assigned_at")
            parsed_ogrn_date = self._parse_iso_date(raw_ogrn_date)
            if parsed_ogrn_date is not None:
                entity.ogrn_assigned_at = parsed_ogrn_date
            else:
                entity.ogrn_assigned_at = None
        entity.inn = data.get("inn") or entity.inn
        entity.okpo = data.get("okpo") or entity.okpo

        if "registration_address_id" in data:
            raw_reg_id = data.get("registration_address_id")
            try:
                entity.registration_address_id = int(raw_reg_id) if raw_reg_id is not None and raw_reg_id != "" else None
            except (TypeError, ValueError):
                entity.registration_address_id = None

        if "address_rf_id" in data:
            raw_addr_id = data.get("address_rf_id")
            try:
                entity.address_rf_id = int(raw_addr_id) if raw_addr_id is not None and raw_addr_id != "" else None
            except (TypeError, ValueError):
                entity.address_rf_id = None

        if "representative_profile_id" in data:
            raw_rep_id = data.get("representative_profile_id")
            try:
                entity.representative_profile_id = int(raw_rep_id) if raw_rep_id is not None and raw_rep_id != "" else None
            except (TypeError, ValueError):
                entity.representative_profile_id = None
        entity.representative_basis = data.get("representative_basis") or entity.representative_basis
        entity.representative_position = data.get("representative_position") or entity.representative_position

        entity.phone = data.get("phone") or entity.phone
        entity.email = data.get("email") or entity.email
        entity.max_contact = data.get("max_contact") or entity.max_contact

        entity.account_number = data.get("account_number") or entity.account_number
        entity.correspondent_account = data.get("correspondent_account") or entity.correspondent_account
        entity.bank_name = data.get("bank_name") or entity.bank_name
        entity.bik = data.get("bik") or entity.bik

    def _apply_sp_details(self, entity: SoleProprietorProfile, data: Dict[str, Any]) -> None:
        entity.last_name = data.get("last_name") or entity.last_name
        entity.first_name = data.get("first_name") or entity.first_name
        entity.middle_name = data.get("middle_name") or entity.middle_name
        entity.gender = data.get("gender") or entity.gender

        entity.ogrnip = data.get("ogrnip") or entity.ogrnip
        entity.inn = data.get("inn") or entity.inn
        entity.okpo = data.get("okpo") or entity.okpo

        if "residence_address_id" in data:
            raw_res_id = data.get("residence_address_id")
            try:
                entity.residence_address_id = int(raw_res_id) if raw_res_id is not None else None
            except (TypeError, ValueError):
                entity.residence_address_id = None

        entity.phone = data.get("phone") or entity.phone
        entity.email = data.get("email") or entity.email
        entity.max_contact = data.get("max_contact") or entity.max_contact

        entity.account_number = data.get("account_number") or entity.account_number
        entity.correspondent_account = data.get("correspondent_account") or entity.correspondent_account
        entity.bank_name = data.get("bank_name") or entity.bank_name
        entity.bik = data.get("bik") or entity.bik

    async def _individual_details_to_dict(self, session: AsyncSession, profile_id: int) -> Dict[str, Any]:
        instance = await self._load_details(session, IndividualProfile, profile_id)
        if not instance:
            return {}

        registration_full: Optional[str] = None
        residence_full: Optional[str] = None
        if instance.registration_address_id:
            res = await session.execute(
                select(Address.full_address).where(Address.id == instance.registration_address_id)
            )
            registration_full = res.scalar_one_or_none()
        if getattr(instance, "residence_address_id", None):
            res2 = await session.execute(
                select(Address.full_address).where(Address.id == instance.residence_address_id)
            )
            residence_full = res2.scalar_one_or_none()

        return {
            "citizenship": instance.citizenship,
            "last_name": instance.last_name,
            "first_name": instance.first_name,
            "middle_name": instance.middle_name,
            "birth_date": instance.birth_date.isoformat() if instance.birth_date else None,
            "gender": instance.gender,
            "is_self_employed": instance.is_self_employed,
            "passport_series": instance.passport_series,
            "passport_number": instance.passport_number,
            "passport_issued_at": instance.passport_issued_at.isoformat() if instance.passport_issued_at else None,
            "passport_issued_by": instance.passport_issued_by,
            "passport_department_code": instance.passport_department_code,
            "registration_address_id": instance.registration_address_id,
            "registration_address_full": registration_full,
            "snils": instance.snils,
            "inn": instance.inn,
            "phone": instance.phone,
            "email": instance.email,
            "max_contact": instance.max_contact,
            "account_number": instance.account_number,
            "correspondent_account": instance.correspondent_account,
            "bank_name": instance.bank_name,
            "bik": instance.bik,
            # Дополнительный адрес проживания (если используется)
            "residence_address_id": getattr(instance, "residence_address_id", None),
            "residence_address_full": residence_full,
        }

    async def _legal_details_to_dict(self, session: AsyncSession, profile_id: int) -> Dict[str, Any]:
        instance = await self._load_details(session, LegalProfile, profile_id)
        if not instance:
            return {}

        reg_full: Optional[str] = None
        rf_full: Optional[str] = None
        if instance.registration_address_id:
            res = await session.execute(
                select(Address.full_address).where(Address.id == instance.registration_address_id)
            )
            reg_full = res.scalar_one_or_none()
        if instance.address_rf_id:
            res2 = await session.execute(
                select(Address.full_address).where(Address.id == instance.address_rf_id)
            )
            rf_full = res2.scalar_one_or_none()

        # Находим profile_id представителя по individual_profiles.id
        representative_profile_profile_id: Optional[int] = None
        if instance.representative_profile_id:
            res_rep = await session.execute(
                select(IndividualProfile.profile_id).where(IndividualProfile.id == instance.representative_profile_id)
            )
            representative_profile_profile_id = res_rep.scalar_one_or_none()

        return {
            "full_name": instance.full_name,
            "ogrn": instance.ogrn,
            "ogrn_assigned_at": instance.ogrn_assigned_at.isoformat() if instance.ogrn_assigned_at else None,
            "inn": instance.inn,
            "okpo": instance.okpo,
            "registration_address_id": instance.registration_address_id,
            "registration_address_full": reg_full,
            "address_rf_id": instance.address_rf_id,
            "address_rf_full": rf_full,
            "representative_profile_id": instance.representative_profile_id,
            "representative_profile_profile_id": representative_profile_profile_id,
            "representative_basis": instance.representative_basis,
            "representative_position": instance.representative_position,
            "phone": instance.phone,
            "email": instance.email,
            "max_contact": instance.max_contact,
            "account_number": instance.account_number,
            "correspondent_account": instance.correspondent_account,
            "bank_name": instance.bank_name,
            "bik": instance.bik,
        }

    async def _sp_details_to_dict(self, session: AsyncSession, profile_id: int) -> Dict[str, Any]:
        instance = await self._load_details(session, SoleProprietorProfile, profile_id)
        if not instance:
            return {}
        residence_full: Optional[str] = None
        if instance.residence_address_id:
            res = await session.execute(
                select(Address.full_address).where(Address.id == instance.residence_address_id)
            )
            residence_full = res.scalar_one_or_none()

        return {
            "last_name": instance.last_name,
            "first_name": instance.first_name,
            "middle_name": instance.middle_name,
            "gender": instance.gender,
            "ogrnip": instance.ogrnip,
            "inn": instance.inn,
            "okpo": instance.okpo,
            "residence_address_id": instance.residence_address_id,
            "residence_address_full": residence_full,
            "phone": instance.phone,
            "email": instance.email,
            "max_contact": instance.max_contact,
            "account_number": instance.account_number,
            "correspondent_account": instance.correspondent_account,
            "bank_name": instance.bank_name,
            "bik": instance.bik,
        }

