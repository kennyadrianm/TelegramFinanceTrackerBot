"""Interactive inline calendar keyboard localized in Bahasa Indonesia for Asia/Jakarta."""

import calendar
from datetime import date
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.timezone import INDONESIAN_MONTH_NAMES, today_wib


def create_calendar(year: int | None = None, month: int | None = None) -> InlineKeyboardMarkup:
    """Generate an inline calendar keyboard for a specific month and year."""
    today = today_wib()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    keyboard: list[list[InlineKeyboardButton]] = []

    # Header: Month and Year navigation
    month_name = INDONESIAN_MONTH_NAMES[month]
    prev_m = 12 if month == 1 else month - 1
    prev_y = year - 1 if month == 1 else year
    next_m = 1 if month == 12 else month + 1
    next_y = year + 1 if month == 12 else year

    keyboard.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal:nav:{prev_y}:{prev_m}"),
        InlineKeyboardButton(text=f"{month_name} {year}", callback_data="cal:ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:nav:{next_y}:{next_m}"),
    ])

    # Day names header (Monday to Sunday)
    weekdays = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data="cal:ignore") for day in weekdays
    ])

    # Calendar matrix (Monday is 0, Sunday is 6)
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    for week in month_days:
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore"))
            else:
                is_today = (day == today.day and month == today.month and year == today.year)
                label = f"•{day}•" if is_today else str(day)
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(text=label, callback_data=f"cal:date:{date_str}"))
        keyboard.append(row)

    # Action footer
    keyboard.append([
        InlineKeyboardButton(text="📅 Gunakan Hari Ini", callback_data="cal:today"),
        InlineKeyboardButton(text="❌ Batalkan", callback_data="cal:cancel"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

