from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from vless_top_bot.adapters.storage.user_repo import UserRepo
from vless_top_bot.bot.handlers import build_router
from vless_top_bot.config.settings import load_settings
from vless_top_bot.services.check_service import CheckService


def main() -> None:
    settings = load_settings()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    user_repo = UserRepo(settings.data_dir)
    check_service = CheckService()

    router = build_router(
        user_repo=user_repo,
        check_service=check_service,
        defaults={
            "top": settings.default_top,
            "attempts": settings.default_attempts,
            "timeout": settings.default_timeout,
            "fetch_timeout": settings.default_fetch_timeout,
            "concurrency": settings.default_concurrency,
        },
    )
    dp.include_router(router)

    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
