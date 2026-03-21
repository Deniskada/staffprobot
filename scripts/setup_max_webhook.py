#!/usr/bin/env python3
"""
Регистрация webhook для MAX бота.
POST /subscriptions к platform-api.max.ru.
"""
import argparse
import asyncio
import os
import sys

import httpx

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="Настройка webhook для MAX бота")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Базовый URL (https://maxdev.staffprobot.ru). Берётся из MAX_WEBHOOK_BASE_URL если не указан.",
    )
    parser.add_argument(
        "--path",
        default="/max/webhook",
        help="Путь webhook (по умолчанию /max/webhook)",
    )
    parser.add_argument(
        "--secret",
        default=None,
        help="Секрет для X-Max-Bot-Api-Secret (опционально)",
    )
    parser.add_argument("--list", action="store_true", help="Показать текущие подписки")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Удалить все подписки кроме указанного --base-url (устраняет дубли сообщений)",
    )
    args = parser.parse_args()

    from core.config.settings import settings

    token = settings.max_bot_token
    if not token:
        print("❌ MAX_BOT_TOKEN не задан в .env")
        sys.exit(1)

    base_url = args.base_url or settings.max_webhook_base_url or "https://maxdev.staffprobot.ru"
    base_url = base_url.rstrip("/")
    path = args.path if args.path.startswith("/") else f"/{args.path}"
    webhook_url = f"{base_url}{path}"

    async def do_list():
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://platform-api.max.ru/subscriptions",
                headers={"Authorization": token},
            )
            return r

    async def do_cleanup(keep_url: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://platform-api.max.ru/subscriptions",
                headers={"Authorization": token},
            )
            if r.status_code != 200:
                return r
            subs = r.json().get("subscriptions", [])
            for s in subs:
                url = s.get("url", "")
                if url and url != keep_url:
                    dr = await client.delete(
                        "https://platform-api.max.ru/subscriptions",
                        params={"url": url},
                        headers={"Authorization": token},
                    )
                    print(f"  Удалено: {url} ({dr.status_code})")
            return r

    if args.list:
        r = asyncio.run(do_list())
        if r.status_code == 200:
            subs = r.json().get("subscriptions", [])
            print(f"Подписок: {len(subs)}")
            for s in subs:
                print(f"  - {s.get('url')}")
        else:
            print(f"❌ {r.status_code}: {r.text}")
        return

    if args.cleanup:
        print(f"Оставляем только: {webhook_url}")
        asyncio.run(do_cleanup(webhook_url))
        return

    payload = {
        "url": webhook_url,
        "update_types": ["message_created", "message_callback", "bot_started"],
    }
    if args.secret:
        payload["secret"] = args.secret

    async def do_setup():
        async with httpx.AsyncClient() as client:
            return await client.post(
                "https://platform-api.max.ru/subscriptions",
                json=payload,
                headers={"Authorization": token, "Content-Type": "application/json"},
            )

    print(f"📤 Регистрация webhook: {webhook_url}")
    r = asyncio.run(do_setup())

    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            print("✅ Webhook зарегистрирован")
        else:
            print(f"⚠️ Ответ: {data}")
    else:
        print(f"❌ Ошибка {r.status_code}: {r.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
