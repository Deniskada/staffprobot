"""
Сервис интеграции веб-приложения с Telegram ботом
"""

import httpx
import asyncio
from typing import Optional
from core.config.settings import settings
from core.logging.logger import logger
from core.utils.url_helper import URLHelper


class BotIntegrationService:
    """Сервис для интеграции с Telegram ботом"""
    
    def __init__(self):
        self.bot_token = getattr(settings, "telegram_bot_token", None)
        self.bot_api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def _pin_message(self, pin_code: str, web_url: str) -> str:
        return f"""🔐 <b>Код для входа в StaffProBot</b>

Ваш PIN-код: <code>{pin_code}</code>

⏰ Код действителен 5 минут
🌐 Сайт: {web_url}

<i>Если вы не запрашивали код, проигнорируйте это сообщение.</i>"""

    async def send_pin_code(
        self, messenger: str, external_id: str, pin_code: str
    ) -> bool:
        """Отправка PIN-кода. messenger: telegram|max."""
        web_url = await URLHelper.get_web_url()
        message = self._pin_message(pin_code, web_url)
        if messenger == "telegram":
            return await self._send_pin_telegram(int(external_id), message)
        if messenger == "max":
            return await self._send_pin_max(external_id, message)
        logger.error(f"Unknown messenger: {messenger}")
        return False

    async def _send_pin_telegram(self, telegram_id: int, message: str) -> bool:
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return False
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self.bot_api_url}/sendMessage",
                    json={"chat_id": telegram_id, "text": message, "parse_mode": "HTML"},
                    timeout=10.0,
                )
                if r.status_code == 200:
                    logger.info(f"PIN sent to TG {telegram_id}")
                    return True
                logger.error(f"TG send PIN failed {telegram_id}: {r.text}")
                return False
        except Exception as e:
            logger.error(f"TG send PIN error {telegram_id}: {e}")
            return False

    async def _send_pin_max(self, user_id: str, message: str) -> bool:
        from shared.bot_unified.max_client import MaxClient

        client = MaxClient()
        try:
            await client.send_to_user(user_id, message, format="html")
            logger.info(f"PIN sent to MAX user {user_id}")
            return True
        except Exception as e:
            logger.error(f"MAX send PIN error {user_id}: {e}")
            return False
    
    async def send_notification(self, telegram_id: int, message: str) -> bool:
        """Отправка уведомления пользователю через бота"""
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.bot_api_url}/sendMessage",
                    json={
                        "chat_id": telegram_id,
                        "text": message,
                        "parse_mode": "HTML"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Notification sent to user {telegram_id}")
                    return True
                else:
                    logger.error(f"Failed to send notification to user {telegram_id}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending notification to user {telegram_id}: {e}")
            return False
