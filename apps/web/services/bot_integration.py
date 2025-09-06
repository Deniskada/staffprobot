"""
Сервис интеграции веб-приложения с Telegram ботом
"""

import httpx
import asyncio
from typing import Optional
from core.config.settings import settings
from core.logging.logger import logger


class BotIntegrationService:
    """Сервис для интеграции с Telegram ботом"""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'telegram_bot_token', None)
        self.bot_api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_pin_code(self, telegram_id: int, pin_code: str) -> bool:
        """Отправка PIN-кода пользователю через бота"""
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return False
        
        message = f"""
🔐 <b>Код для входа в StaffProBot</b>

Ваш PIN-код: <code>{pin_code}</code>

⏰ Код действителен 5 минут
🌐 Сайт: http://localhost:8001

<i>Если вы не запрашивали код, проигнорируйте это сообщение.</i>
"""
        
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
                    logger.info(f"PIN code sent to user {telegram_id}")
                    return True
                else:
                    logger.error(f"Failed to send PIN code to user {telegram_id}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending PIN code to user {telegram_id}: {e}")
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
