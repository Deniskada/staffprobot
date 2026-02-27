"""Клиент Yandex GPT для генерации текстов."""

import httpx
from typing import Optional

from core.config.settings import settings
from core.logging.logger import logger

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

BIRTHDAY_SYSTEM_PROMPT = (
    "Роль: Ты — корпоративный копирайтер и профессиональный коуч по личностному росту.\n"
    "Задача: Напиши уникальное, жизнеутверждающих и мотивирующих поздравление с Днем Рождения "
    "для сотрудника компании. Избегай общих фраз и банальностей («желаем счастья, здоровья»)."
)

HOLIDAY_SYSTEM_PROMPT = (
    "Роль: Ты — корпоративный копирайтер компании.\n"
    "Задача: Напиши короткое (3-5 предложений), искреннее и нешаблонное поздравление коллективу "
    "с государственным праздником. Избегай штампов и канцелярита. Текст должен быть тёплым, "
    "живым и вдохновляющим."
)


async def generate_birthday_greeting(first_name: str, last_name: Optional[str] = None) -> Optional[str]:
    """Сгенерировать поздравление с ДР через Yandex GPT.

    Returns:
        Текст поздравления или None при ошибке.
    """
    folder_id = settings.yandex_gpt_folder_id
    api_key = settings.yandex_gpt_api_key

    if not folder_id or not api_key:
        logger.warning("Yandex GPT не настроен (YANDEX_GPT_FOLDER_ID / YANDEX_GPT_API_KEY)")
        return None

    full_name = f"{first_name} {last_name}".strip() if last_name else first_name
    user_prompt = f"Напиши поздравление с Днём Рождения для сотрудника {full_name}"

    payload = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.8,
            "maxTokens": "500",
        },
        "messages": [
            {"role": "system", "text": BIRTHDAY_SYSTEM_PROMPT},
            {"role": "user", "text": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_GPT_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            text = data["result"]["alternatives"][0]["message"]["text"]
            return text.strip()
    except httpx.HTTPStatusError as e:
        logger.error(f"Yandex GPT HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Yandex GPT error: {e}")

    return None


async def generate_holiday_greeting(holiday_name: str) -> Optional[str]:
    """Сгенерировать поздравление с государственным праздником через Yandex GPT."""
    folder_id = settings.yandex_gpt_folder_id
    api_key = settings.yandex_gpt_api_key

    if not folder_id or not api_key:
        logger.warning("Yandex GPT не настроен")
        return None

    payload = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.8,
            "maxTokens": "500",
        },
        "messages": [
            {"role": "system", "text": HOLIDAY_SYSTEM_PROMPT},
            {"role": "user", "text": f"Напиши поздравление коллективу с праздником: {holiday_name}"},
        ],
    }

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_GPT_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            text = data["result"]["alternatives"][0]["message"]["text"]
            return text.strip()
    except httpx.HTTPStatusError as e:
        logger.error(f"Yandex GPT HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Yandex GPT holiday error: {e}")

    return None
