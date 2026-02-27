"""Генерация PDF подписанного договора (HTML → PDF через weasyprint)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional

from core.logging.logger import logger


_CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: 'DejaVu Sans', 'Liberation Sans', Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #222; }
h2 { text-align: center; margin-bottom: 0.5em; }
h3 { margin-top: 1.2em; }
p { text-align: justify; margin: 0.3em 0; }
.pep-block { margin-top: 2em; padding: 1em; border: 1px solid #999; background: #f9f9f9; font-size: 9pt; }
.pep-block strong { display: inline-block; min-width: 180px; }
"""


def _render_pep_block(pep_metadata: Dict[str, Any]) -> str:
    """Блок «Подписано ПЭП» для вставки в конец PDF."""
    channel = pep_metadata.get("channel", "—")
    signed_at = pep_metadata.get("signed_at", "—")
    otp_hash_short = (pep_metadata.get("otp_hash") or "")[:16] + "..."
    signed_ip = pep_metadata.get("signed_ip", "—")
    esia_oid = pep_metadata.get("esia_oid", "—")

    return f"""<div class="pep-block">
<p><strong>Подписано простой электронной подписью (ПЭП)</strong></p>
<p><strong>Дата подписания:</strong> {signed_at}</p>
<p><strong>Канал подтверждения:</strong> {channel}</p>
<p><strong>Хеш OTP:</strong> {otp_hash_short}</p>
<p><strong>IP подписанта:</strong> {signed_ip}</p>
<p><strong>Идентификатор ЕСИА:</strong> {esia_oid}</p>
</div>"""


class ContractPdfService:
    """Генерация PDF из HTML-содержимого договора."""

    async def generate_pdf(
        self,
        contract_html: str,
        pep_metadata: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Сгенерировать PDF из HTML-контента договора.

        Args:
            contract_html: HTML-текст договора.
            pep_metadata: Метаданные ПЭП (вставляются в конец документа).

        Returns:
            bytes — содержимое PDF-файла.
        """
        import weasyprint

        pep_block = _render_pep_block(pep_metadata) if pep_metadata else ""

        full_html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
{contract_html}
{pep_block}
</body>
</html>"""

        try:
            doc = weasyprint.HTML(string=full_html)
            pdf_bytes = doc.write_pdf()
            logger.info("Contract PDF generated", size=len(pdf_bytes))
            return pdf_bytes
        except Exception as e:
            logger.error("PDF generation failed", error=str(e))
            raise

    async def generate_and_upload(
        self,
        contract_html: str,
        contract_id: int,
        version: str,
        pep_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Сгенерировать PDF и загрузить в S3.

        Returns:
            S3 file_key.
        """
        from shared.services.media_storage import get_media_storage_client

        pdf_bytes = await self.generate_pdf(contract_html, pep_metadata)
        file_name = f"signed_{version}.pdf"
        folder = f"contracts/{contract_id}"

        storage = get_media_storage_client()
        media_file = await storage.upload(
            file_content=pdf_bytes,
            file_name=file_name,
            content_type="application/pdf",
            folder=folder,
            metadata={"contract_id": contract_id, "version": version},
        )
        logger.info(
            "Contract PDF uploaded to S3",
            contract_id=contract_id,
            file_key=media_file.key,
        )
        return media_file.key
