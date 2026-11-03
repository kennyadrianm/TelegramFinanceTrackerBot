"""Middleware to restrict bot usage strictly to Telegram private chats."""

import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class PrivateChatOnlyMiddleware(BaseMiddleware):
    """Rejects interactions coming from groups, supergroups, or channels."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        if chat and chat.type != ChatType.PRIVATE:
            logger.warning(
                "Rejected interaction from non-private chat id=%d, type=%s",
                chat.id,
                chat.type,
            )
            if isinstance(event, Message):
                try:
                    await event.reply(
                        "⚠️ *Akses Ditolak*\n\n"
                        "Finance Tracker Bot hanya dapat digunakan melalui percakapan pribadi (Private Chat) demi privasi keuangan Anda.",
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        "Bot hanya dapat digunakan di Private Chat.",
                        show_alert=True,
                    )
                except Exception:
                    pass
            return None

        return await handler(event, data)

