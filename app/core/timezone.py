"""Timezone utilities and date calculation helpers strictly using Asia/Jakarta (WIB)."""

from datetime import date, datetime, time, timedelta
import calendar
import zoneinfo

JAKARTA_TZ = zoneinfo.ZoneInfo("Asia/Jakarta")

INDONESIAN_MONTH_NAMES = [
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]

INDONESIAN_DAY_NAMES = [
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
    "Minggu",
]


def now_wib() -> datetime:
    """Return the current datetime localized in Asia/Jakarta."""
    return datetime.now(JAKARTA_TZ)


def today_wib() -> date:
    """Return today's date in Asia/Jakarta."""
    return now_wib().date()


def parse_date_str(date_str: str) -> date | None:
    """Parse a date string in DD-MM-YYYY or DD/MM/YYYY format."""
    cleaned = date_str.strip().replace("/", "-")
    parts = cleaned.split("-")
    if len(parts) != 3:
        return None
    try:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        if year < 100:
            year += 2000
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def format_date_id(d: date) -> str:
    """Format date as DD-MM-YYYY."""
    return d.strftime("%d-%m-%Y")


def format_date_long_id(d: date) -> str:
    """Format date as '25 Oktober 2026'."""
    month_name = INDONESIAN_MONTH_NAMES[d.month]
    return f"{d.day} {month_name} {d.year}"


def get_week_range(target_date: date) -> tuple[date, date]:
    """Return (Monday, Sunday) date range for the week containing target_date.
    
    Monday is weekday 0, Sunday is weekday 6.
    """
    weekday = target_date.weekday()
    monday = target_date - timedelta(days=weekday)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_month_range(target_date: date) -> tuple[date, date]:
    """Return (1st_day, last_day) of the calendar month containing target_date."""
    first_day = date(target_date.year, target_date.month, 1)
    _, last_day_num = calendar.monthrange(target_date.year, target_date.month)
    last_day = date(target_date.year, target_date.month, last_day_num)
    return first_day, last_day


def is_last_day_of_month(target_date: date) -> bool:
    """Check if target_date is the last calendar day of its month."""
    _, last_day_num = calendar.monthrange(target_date.year, target_date.month)
    return target_date.day == last_day_num

