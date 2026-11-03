"""Reply keyboards for standard Telegram menus."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.constants import (
    BTN_ADD_TX,
    BTN_CATEGORIES,
    BTN_DASHBOARD,
    BTN_EXPORT,
    BTN_HISTORY,
    BTN_REPORT,
    BTN_SETTINGS,
)


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the persistent bottom reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DASHBOARD), KeyboardButton(text=BTN_ADD_TX)],
            [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_REPORT)],
            [KeyboardButton(text=BTN_EXPORT), KeyboardButton(text=BTN_CATEGORIES)],
            [KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

