"""Сервис простой электронной подписи (ПЭП) с абстракцией каналов доставки OTP."""

from __future__ import annotations

import hashlib
import json
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as redis

from core.config.settings import settings
from core.logging.logger import logger


class PepChannel(ABC):
    """Абстрактный канал доставки OTP-кода."""

    channel_key: str = "base"

    @abstractmethod
    async def send_otp(self, user_id: int, telegram_id: int, code: str) -> bool:
        """Отправить OTP-код пользователю. Возвращает True при успехе."""
        ...


class TelegramPepChannel(PepChannel):
    """OTP через Telegram-бот."""

    channel_key = "telegram"

    def __init__(self, bot: Any = None) -> None:
        self._bot = bot

    async def send_otp(self, user_id: int, telegram_id: int, code: str) -> bool:
        if not self._bot:
            logger.error("PEP Telegram channel: bot not provided", user_id=user_id)
            return False
        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"🔐 Код подтверждения подписания договора: *{code}*\n\n"
                    "Никому не сообщайте этот код. Код действителен 5 минут."
                ),
                parse_mode="Markdown",
            )
            logger.info("PEP OTP sent via Telegram", user_id=user_id)
            return True
        except Exception as e:
            logger.error("PEP Telegram send failed", user_id=user_id, error=str(e))
            return False


class SmsPepChannel(PepChannel):
    """OTP через SMS (заглушка для будущей реализации)."""

    channel_key = "sms"

    async def send_otp(self, user_id: int, telegram_id: int, code: str) -> bool:
        # TODO: интеграция с SMS-провайдером
        logger.warning("SMS PEP channel not implemented yet", user_id=user_id)
        return False


class PepService:
    """Сервис ПЭП: генерация, отправка и проверка OTP-кодов."""

    OTP_LENGTH = 6
    OTP_TTL = 300  # 5 минут
    MAX_ATTEMPTS = 3

    def __init__(
        self,
        channel: Optional[PepChannel] = None,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        self.channel = channel or TelegramPepChannel()
        self._redis = redis_client

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _key(self, user_id: int, contract_id: int) -> str:
        return f"pep:{user_id}:{contract_id}"

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    async def initiate_signing(
        self, user_id: int, telegram_id: int, contract_id: int
    ) -> Dict[str, Any]:
        """Сгенерировать OTP, сохранить в Redis, отправить через канал."""
        code = "".join([str(secrets.randbelow(10)) for _ in range(self.OTP_LENGTH)])
        r = await self._get_redis()
        key = self._key(user_id, contract_id)

        payload = json.dumps({
            "code_hash": self._hash_code(code),
            "attempts": 0,
            "channel": self.channel.channel_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await r.setex(key, self.OTP_TTL, payload)

        sent = await self.channel.send_otp(user_id, telegram_id, code)
        if not sent:
            await r.delete(key)
            return {"status": "send_failed", "channel": self.channel.channel_key}

        logger.info(
            "PEP signing initiated",
            user_id=user_id,
            contract_id=contract_id,
            channel=self.channel.channel_key,
        )
        return {"status": "sent", "channel": self.channel.channel_key}

    async def verify_otp(
        self, user_id: int, contract_id: int, code: str, client_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """Проверить OTP. Возвращает статус и метаданные при успехе."""
        r = await self._get_redis()
        key = self._key(user_id, contract_id)
        raw = await r.get(key)

        if not raw:
            return {"status": "expired", "valid": False}

        data = json.loads(raw)
        attempts = data.get("attempts", 0)

        if attempts >= self.MAX_ATTEMPTS:
            await r.delete(key)
            return {"status": "max_attempts", "valid": False}

        if self._hash_code(code) != data.get("code_hash"):
            data["attempts"] = attempts + 1
            await r.setex(key, self.OTP_TTL, json.dumps(data))
            remaining = self.MAX_ATTEMPTS - data["attempts"]
            return {"status": "invalid", "valid": False, "attempts_remaining": remaining}

        # Успех — удаляем ключ и возвращаем метаданные для pep_metadata
        await r.delete(key)
        now = datetime.now(timezone.utc)
        pep_metadata = {
            "channel": data.get("channel", self.channel.channel_key),
            "otp_hash": data.get("code_hash"),
            "signed_at": now.isoformat(),
            "signed_ip": client_ip,
        }
        logger.info(
            "PEP OTP verified",
            user_id=user_id,
            contract_id=contract_id,
            channel=pep_metadata["channel"],
        )
        return {"status": "verified", "valid": True, "pep_metadata": pep_metadata}
