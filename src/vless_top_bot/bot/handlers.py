from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

logger = logging.getLogger(__name__)

from vless_top_bot.adapters.storage.user_repo import UserRepo
from vless_top_bot.services.check_service import CheckService


def build_router(user_repo: UserRepo, check_service: CheckService, defaults: dict) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer(
            "Привет. Команды:\n"
            "/setsub <url> — сохранить подписку\n"
            "/check — проверить и выдать ТОП"
        )

    @router.message(Command("setsub"))
    async def cmd_setsub(message: Message):
        text = (message.text or "").strip()
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Использование: /setsub <subscription_url>")
            return

        url = parts[1].strip()
        user_repo.set_subscription(message.from_user.id, url)
        await message.answer("Сохранил подписку ✅")

    @router.message(Command("check"))
    async def cmd_check(message: Message):
        sub = user_repo.get_subscription(message.from_user.id)
        if not sub:
            await message.answer("Сначала задай подписку: /setsub <url> или просто отправь URL сообщением")
            return

        await message.answer("Запускаю проверку, это может занять до минуты…")
        try:
            report, links = await check_service.run_check(
                subscription_url=sub,
                top=defaults["top"],
                attempts=defaults["attempts"],
                timeout=defaults["timeout"],
                fetch_timeout=defaults["fetch_timeout"],
                concurrency=defaults["concurrency"],
                youtube_check_timeout=defaults["youtube_check_timeout"],
                youtube_tunnel_start_timeout=defaults["youtube_tunnel_start_timeout"],
                youtube_strict_mode=defaults["youtube_strict_mode"],
                youtube_strict_attempts=defaults["youtube_strict_attempts"],
            )
        except Exception:
            await message.answer("Проверка упала по таймауту/сети. Попробуй ещё раз через минуту.")
            return

        await message.answer(report)

        if links:
            # 1) Пытаемся отправить txt-файл для удобного копирования/импорта
            payload = ("\n".join(links) + "\n").encode("utf-8")
            doc = BufferedInputFile(payload, filename="top_vless.txt")
            try:
                await message.answer_document(doc, caption="ТОП ссылки файлом")
            except Exception as e:
                logger.exception("Не удалось отправить файл top_vless.txt")
                await message.answer(f"Не смог отправить файл со ссылками: {e}")

            # 2) Дублируем каждую ссылку отдельным сообщением (даже если файл не ушёл)
            for idx, link in enumerate(links, start=1):
                try:
                    await message.answer(f"Ключ {idx}:\n{link}")
                except Exception:
                    logger.exception("Не удалось отправить ключ %s", idx)

    @router.message()
    async def catch_subscription_url(message: Message):
        text = (message.text or "").strip()
        if text.startswith("http://") or text.startswith("https://"):
            user_repo.set_subscription(message.from_user.id, text)
            await message.answer("Сохранил подписку ✅ Теперь запусти /check")

    return router
