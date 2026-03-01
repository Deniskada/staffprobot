"""Сервис загрузки и управления документами профиля (сканы паспорта, ИНН, СНИЛС)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging.logger import logger
from domain.entities.profile import Profile
from domain.entities.profile_document import ProfileDocument
from shared.services.media_storage.s3_client import S3MediaStorageClient

ALLOWED_DOCUMENT_TYPES = ("passport_main", "passport_registration", "inn_scan", "snils_scan")

DOCUMENT_TYPE_LABELS = {
    "passport_main": "Паспорт (главная страница)",
    "passport_registration": "Паспорт (прописка)",
    "inn_scan": "ИНН",
    "snils_scan": "СНИЛС",
}

ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp", "application/pdf")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class ProfileDocumentService:
    """Загрузка, просмотр и удаление сканов документов профиля."""

    def __init__(self, s3_provider: str | None = None) -> None:
        if s3_provider is None:
            from core.config.settings import settings
            provider = settings.media_storage_provider
            s3_provider = "minio" if provider == "minio" else "s3"
        self._s3 = S3MediaStorageClient(provider=s3_provider)

    async def upload_document(
        self,
        session: AsyncSession,
        profile_id: int,
        document_type: str,
        file_content: bytes,
        filename: str,
        mime_type: str,
    ) -> Dict[str, Any]:
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(f"Недопустимый тип документа: {document_type}")
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError("Допустимые форматы: JPEG, PNG, WebP, PDF")
        if len(file_content) > MAX_FILE_SIZE:
            raise ValueError("Файл слишком большой (макс. 10 МБ)")

        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        s3_filename = f"{document_type}_{uuid.uuid4().hex[:12]}.{ext}"
        folder = f"profiles/{profile_id}/documents"

        media_file = await self._s3.upload(
            file_content=file_content,
            file_name=s3_filename,
            content_type=mime_type,
            folder=folder,
        )

        # Удаляем предыдущий скан того же типа (замена)
        old_docs = await session.execute(
            select(ProfileDocument).where(
                ProfileDocument.profile_id == profile_id,
                ProfileDocument.document_type == document_type,
            )
        )
        for old_doc in old_docs.scalars().all():
            try:
                await self._s3.delete(old_doc.file_key)
            except Exception:
                pass
            await session.delete(old_doc)

        doc = ProfileDocument(
            profile_id=profile_id,
            document_type=document_type,
            file_key=media_file.key,
            original_filename=filename,
            mime_type=mime_type,
        )
        session.add(doc)
        await session.commit()

        logger.info("Profile document uploaded", profile_id=profile_id, type=document_type)
        return {
            "id": doc.id,
            "document_type": document_type,
            "label": DOCUMENT_TYPE_LABELS.get(document_type, document_type),
            "file_key": doc.file_key,
            "original_filename": doc.original_filename,
            "url": media_file.url,
        }

    async def get_documents(
        self, session: AsyncSession, profile_id: int
    ) -> List[Dict[str, Any]]:
        result = await session.execute(
            select(ProfileDocument)
            .where(ProfileDocument.profile_id == profile_id)
            .order_by(ProfileDocument.document_type)
        )
        docs = result.scalars().all()
        out = []
        for d in docs:
            url = await self._s3.get_url(d.file_key)
            out.append({
                "id": d.id,
                "document_type": d.document_type,
                "label": DOCUMENT_TYPE_LABELS.get(d.document_type, d.document_type),
                "file_key": d.file_key,
                "original_filename": d.original_filename,
                "url": url,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            })
        return out

    async def delete_document(
        self, session: AsyncSession, document_id: int, profile_id: int
    ) -> bool:
        result = await session.execute(
            select(ProfileDocument).where(
                ProfileDocument.id == document_id,
                ProfileDocument.profile_id == profile_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        try:
            await self._s3.delete(doc.file_key)
        except Exception:
            pass

        await session.delete(doc)
        await session.commit()
        logger.info("Profile document deleted", document_id=document_id, profile_id=profile_id)
        return True

    async def get_missing_documents(
        self, session: AsyncSession, profile_id: int
    ) -> List[Dict[str, str]]:
        """Вернуть список типов документов, которые ещё не загружены."""
        result = await session.execute(
            select(ProfileDocument.document_type)
            .where(ProfileDocument.profile_id == profile_id)
        )
        existing = {row[0] for row in result.fetchall()}
        missing = []
        for doc_type in ALLOWED_DOCUMENT_TYPES:
            if doc_type not in existing:
                missing.append({
                    "document_type": doc_type,
                    "label": DOCUMENT_TYPE_LABELS[doc_type],
                })
        return missing
