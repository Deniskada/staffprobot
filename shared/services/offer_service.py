"""Сервис работы с офертами: валидация реквизитов, акцепт, уведомления."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging.logger import logger
from domain.entities.contract import Contract, ContractTemplate, ContractVersion
from domain.entities.contract_type import ContractType
from domain.entities.profile import Profile, IndividualProfile
from domain.entities.user import User


# Обязательные поля IndividualProfile для подписания оферты (п. 12.5)
REQUIRED_INDIVIDUAL_FIELDS: List[Tuple[str, str]] = [
    ("last_name", "Фамилия"),
    ("first_name", "Имя"),
    ("gender", "Пол"),
    ("birth_date", "Дата рождения"),
    ("passport_series", "Серия паспорта"),
    ("passport_number", "Номер паспорта"),
    ("passport_issued_at", "Дата выдачи паспорта"),
    ("passport_issued_by", "Кем выдан паспорт"),
    ("inn", "ИНН"),
    ("snils", "СНИЛС"),
    ("phone", "Телефон"),
    ("email", "Электронная почта"),
    ("account_number", "Расчётный счёт"),
    ("bik", "БИК банка"),
]

REQUIRED_ADDRESS_LABEL = "Адрес регистрации"


class OfferService:
    """Сервис оферт: проверка реквизитов, создание, акцепт."""

    async def validate_employee_profile(
        self, session: AsyncSession, user_id: int
    ) -> Dict[str, Any]:
        """
        Проверить заполненность обязательных реквизитов сотрудника.

        Returns:
            {"complete": bool, "missing_fields": [{"field": ..., "label": ...}], "profile_id": int|None}
        """
        # Ищем дефолтный individual-профиль сотрудника
        stmt = (
            select(Profile)
            .where(
                Profile.user_id == user_id,
                Profile.profile_type == "individual",
                Profile.is_archived.is_(False),
            )
            .order_by(Profile.is_default.desc(), Profile.id)
        )
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            return {
                "complete": False,
                "missing_fields": [{"field": "profile", "label": "Профиль не создан"}],
                "profile_id": None,
            }

        # Загружаем IndividualProfile
        ip_stmt = select(IndividualProfile).where(IndividualProfile.profile_id == profile.id)
        ip_result = await session.execute(ip_stmt)
        ip = ip_result.scalar_one_or_none()

        if not ip:
            return {
                "complete": False,
                "missing_fields": [{"field": "individual_profile", "label": "Реквизиты ФЛ не заполнены"}],
                "profile_id": profile.id,
            }

        missing: List[Dict[str, str]] = []
        for field_name, label in REQUIRED_INDIVIDUAL_FIELDS:
            val = getattr(ip, field_name, None)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append({"field": field_name, "label": label})

        # Проверка адреса регистрации
        if not ip.registration_address_id:
            missing.append({"field": "registration_address", "label": REQUIRED_ADDRESS_LABEL})

        # Проверка загруженных сканов документов (без создания S3-клиента)
        from shared.services.profile_document_service import ALLOWED_DOCUMENT_TYPES, DOCUMENT_TYPE_LABELS
        from domain.entities.profile_document import ProfileDocument
        doc_result = await session.execute(
            select(ProfileDocument.document_type)
            .where(ProfileDocument.profile_id == profile.id)
        )
        existing_docs = {row[0] for row in doc_result.fetchall()}
        missing_docs = [
            {"document_type": dt, "label": DOCUMENT_TYPE_LABELS[dt]}
            for dt in ALLOWED_DOCUMENT_TYPES if dt not in existing_docs
        ]

        return {
            "complete": len(missing) == 0 and len(missing_docs) == 0,
            "missing_fields": missing,
            "missing_documents": missing_docs,
            "profile_id": profile.id,
        }

    async def get_contract_for_acceptance(
        self, session: AsyncSession, contract_id: int, employee_user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Получить договор-оферту для просмотра/подписания сотрудником.

        Возвращает данные договора, если он pending_acceptance и принадлежит сотруднику.
        """
        stmt = (
            select(Contract, ContractTemplate)
            .outerjoin(ContractTemplate, Contract.template_id == ContractTemplate.id)
            .where(
                Contract.id == contract_id,
                Contract.employee_id == employee_user_id,
            )
        )
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            return None

        contract, template = row
        # Определяем тип оферты (через шаблон → тип договора)
        is_offer = False
        if template and template.contract_type_id:
            ct_stmt = select(ContractType).where(ContractType.id == template.contract_type_id)
            ct_result = await session.execute(ct_stmt)
            ct = ct_result.scalar_one_or_none()
            is_offer = ct and ct.code == "offer"
        # Fallback: если статус pending_acceptance — считаем офертой
        if not is_offer and contract.status == "pending_acceptance":
            is_offer = True

        # Получаем file_key подписанного PDF из последней версии
        signed_pdf_key = None
        if contract.status == "active":
            ver_stmt = (
                select(ContractVersion.file_key)
                .where(ContractVersion.contract_id == contract.id, ContractVersion.file_key.isnot(None))
                .order_by(ContractVersion.created_at.desc())
                .limit(1)
            )
            ver_result = await session.execute(ver_stmt)
            signed_pdf_key = ver_result.scalar_one_or_none()

        return {
            "id": contract.id,
            "contract_number": contract.contract_number,
            "title": contract.title,
            "content": (template.content if template and template.content and "<" in template.content else None) or contract.content or "",
            "status": contract.status,
            "is_offer": is_offer,
            "template_name": template.name if template else None,
            "start_date": contract.start_date,
            "signed_at": contract.signed_at,
            "owner_id": contract.owner_id,
            "signed_pdf_key": signed_pdf_key,
            "expires_at": contract.expires_at,
        }

    async def accept_offer(
        self,
        session: AsyncSession,
        contract_id: int,
        employee_user_id: int,
        pep_metadata: Dict[str, Any],
        employee_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Принять оферту: обновить статус, подставить реквизиты, создать версию.

        Args:
            contract_id: ID договора
            employee_user_id: внутренний user_id сотрудника
            pep_metadata: метаданные ПЭП из PepService.verify_otp()
            employee_details: реквизиты сотрудника для вставки в текст

        Returns:
            {"status": "accepted", "contract_id": ..., "file_key": ...}
        """
        stmt = select(Contract).where(
            Contract.id == contract_id,
            Contract.employee_id == employee_user_id,
            Contract.status == "pending_acceptance",
        )
        result = await session.execute(stmt)
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError("Договор не найден или уже подписан")

        now = datetime.now(timezone.utc)

        # Подставляем реквизиты сотрудника в текст
        content = contract.content or ""
        for key, value in employee_details.items():
            placeholder = "{{ " + key + " }}"
            if placeholder in content:
                content = content.replace(placeholder, str(value) if value else "")

        # Обновляем договор
        contract.content = content
        contract.status = "active"
        contract.is_active = True
        contract.signed_at = now
        contract.pep_metadata = pep_metadata

        # Генерируем PDF и загружаем в S3
        file_key = None
        try:
            from shared.services.contract_pdf_service import ContractPdfService
            pdf_service = ContractPdfService()
            file_key = await pdf_service.generate_and_upload(
                contract_html=content,
                contract_id=contract.id,
                version="1.0",
                pep_metadata=pep_metadata,
            )
        except Exception as e:
            logger.error("PDF generation failed during offer acceptance", error=str(e))
            # Не блокируем подписание при ошибке PDF

        # Создаём версию
        version = ContractVersion(
            contract_id=contract.id,
            version_number="1.0",
            content=content,
            changes_description="Акцепт оферты (ПЭП)",
            file_key=file_key,
            created_by=employee_user_id,
        )
        session.add(version)

        # Логируем событие подписания
        from shared.services.contract_history_service import log_contract_event
        from domain.entities.contract_history import ContractChangeType
        await log_contract_event(
            session, contract.id, ContractChangeType.SIGNED,
            changed_by=employee_user_id,
            details={"file_key": file_key},
            metadata=pep_metadata,
        )

        await session.commit()
        logger.info(
            "Offer accepted",
            contract_id=contract.id,
            employee_user_id=employee_user_id,
        )
        return {
            "status": "accepted",
            "contract_id": contract.id,
            "file_key": file_key,
        }

    async def reject_offer(
        self,
        session: AsyncSession,
        contract_id: int,
        employee_user_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """Отказ от оферты с указанием причины."""
        stmt = select(Contract).where(
            Contract.id == contract_id,
            Contract.employee_id == employee_user_id,
            Contract.status == "pending_acceptance",
        )
        result = await session.execute(stmt)
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError("Оферта не найдена или уже обработана")

        contract.status = "rejected"
        contract.rejection_reason = reason

        from shared.services.contract_history_service import log_contract_event
        from domain.entities.contract_history import ContractChangeType
        await log_contract_event(
            session, contract.id, ContractChangeType.REJECTED,
            changed_by=employee_user_id,
            details={"reason": reason},
        )

        await session.commit()
        logger.info("Offer rejected", contract_id=contract.id, employee_user_id=employee_user_id)

        # Имя сотрудника для уведомления
        employee_name = ""
        try:
            ip_details = await self.get_employee_details_for_contract(session, employee_user_id)
            employee_name = ip_details.get("employee_fio", "")
        except Exception:
            pass

        return {
            "status": "rejected",
            "contract_id": contract.id,
            "owner_id": contract.owner_id,
            "employee_name": employee_name,
        }

    async def get_employee_details_for_contract(
        self, session: AsyncSession, user_id: int
    ) -> Dict[str, str]:
        """Получить реквизиты сотрудника для подстановки в текст оферты."""
        stmt = (
            select(IndividualProfile)
            .join(Profile, IndividualProfile.profile_id == Profile.id)
            .where(
                Profile.user_id == user_id,
                Profile.profile_type == "individual",
                Profile.is_archived.is_(False),
            )
            .order_by(Profile.is_default.desc())
        )
        result = await session.execute(stmt)
        ip = result.scalars().first()
        if not ip:
            return {}

        middle = f" {ip.middle_name}" if ip.middle_name else ""
        return {
            "employee_fio": f"{ip.last_name} {ip.first_name}{middle}",
            "employee_passport": f"{ip.passport_series} {ip.passport_number}",
            "employee_passport_issued": f"{ip.passport_issued_by}, {ip.passport_issued_at.strftime('%d.%m.%Y') if ip.passport_issued_at else ''}",
            "employee_snils": ip.snils or "",
            "employee_phone": ip.phone or "",
            "employee_email": ip.email or "",
            "employee_account_number": ip.account_number or "",
            "employee_bik": ip.bik or "",
        }
