import asyncio


async def _run() -> None:
    from apps.bot.bot import start_bot
    await start_bot()


if __name__ == "__main__":
    asyncio.run(_run())


