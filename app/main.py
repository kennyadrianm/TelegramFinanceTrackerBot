"""Main application entry point for the Finance Tracker Telegram Bot."""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.session import async_session_factory, engine, init_db
from app.handlers import get_main_router
from app.middlewares.chat_type import PrivateChatOnlyMiddleware
from app.middlewares.db_session import DatabaseSessionMiddleware

logger = logging.getLogger("app")


async def main() -> None:
    """Initialize resources and run the Telegram bot."""
    setup_logging()
    logger.info("Starting Finance Tracker Bot...")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error(
            "BOT_TOKEN tidak ditemukan atau belum dikonfigurasi! "
            "Harap buat file .env dan isi BOT_TOKEN Anda dari @BotFather."
        )
        print(
            "\n"
            "====================================================================\n"
            " PERINGATAN: BOT_TOKEN BELUM DIKONFIGURASI!\n"
            " Harap buka file .env dan masukkan token bot Telegram Anda:\n"
            " BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            "====================================================================\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # 1. Initialize SQLite Database
    await init_db()

    # 2. Setup Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Setup Middlewares
    private_chat_mw = PrivateChatOnlyMiddleware()
    db_mw = DatabaseSessionMiddleware(async_session_factory)

    dp.message.outer_middleware(private_chat_mw)
    dp.callback_query.outer_middleware(private_chat_mw)

    dp.message.middleware(db_mw)
    dp.callback_query.middleware(db_mw)

    # 4. Include Routers
    main_router = get_main_router()
    dp.include_router(main_router)

    # 5. Start Background Scheduler for automatic reports
    start_scheduler(bot)

    # 6. Start Polling
    try:
        logger.info("Bot is now polling for updates in private chats...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping bot execution...")
    finally:
        stop_scheduler()
        await bot.session.close()
        await engine.dispose()
        logger.info("Bot stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

