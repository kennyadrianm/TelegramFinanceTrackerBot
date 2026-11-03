"""Settings handler for configuring automatic financial report schedules."""

import logging
import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_SETTINGS
from app.keyboards.inline_keyboards import get_settings_keyboard
from app.services.report_service import ReportService
from app.services.user_service import UserService
from app.states.form_states import SettingsState

logger = logging.getLogger(__name__)
router = Router(name="settings_router")

TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@router.message(F.text == BTN_SETTINGS)
@router.message(Command("pengaturan"))
async def show_settings_menu(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Show automatic report settings."""
    await state.clear()
    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Silakan mulai bot dengan /start.")
        return

    pref = await ReportService.get_or_create_preference(session, user.id)

    info_text = (
        "⚙️ *PENGATURAN LAPORAN OTOMATIS*\n\n"
        "Anda dapat mengaktifkan pengiriman laporan keuangan berkala langsung ke chat ini secara otomatis.\n\n"
        "💡 *Informasi Penting:*\n"
        "Laporan otomatis dikirim sesuai waktu lokal *Asia/Jakarta (WIB)* "
        "selama bot dan koneksi internet aktif di komputer Anda.\n\n"
        "Klik tombol di bawah untuk mengaktifkan/menonaktifkan atau mengatur waktu pengiriman:"
    )

    await message.answer(
        info_text,
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(pref),
    )


# --- Toggle switches ---
@router.callback_query(F.data == "set:toggle:daily")
async def toggle_daily_report(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    pref = await ReportService.get_or_create_preference(session, user.id)
    pref.daily_enabled = not pref.daily_enabled
    await session.flush()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(pref))
    status = "diaktifkan" if pref.daily_enabled else "dinonaktifkan"
    await callback.answer(f"Laporan Harian {status}!")


@router.callback_query(F.data == "set:toggle:weekly")
async def toggle_weekly_report(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    pref = await ReportService.get_or_create_preference(session, user.id)
    pref.weekly_enabled = not pref.weekly_enabled
    await session.flush()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(pref))
    status = "diaktifkan" if pref.weekly_enabled else "dinonaktifkan"
    await callback.answer(f"Laporan Mingguan {status}!")


@router.callback_query(F.data == "set:toggle:monthly")
async def toggle_monthly_report(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    pref = await ReportService.get_or_create_preference(session, user.id)
    pref.monthly_enabled = not pref.monthly_enabled
    await session.flush()
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(pref))
    status = "diaktifkan" if pref.monthly_enabled else "dinonaktifkan"
    await callback.answer(f"Laporan Bulanan {status}!")


# --- Customize Time ---
@router.callback_query(F.data == "set:time:daily")
async def prompt_daily_time(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.set_state(SettingsState.waiting_for_daily_time)
    await callback.message.edit_text(
        "⏱ *ATUR JAM LAPORAN HARIAN*\n\n"
        "Masukkan jam pengiriman dalam format 24-jam `HH:MM` WIB (contoh: `21:00` atau `08:30`):",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(SettingsState.waiting_for_daily_time)
async def handle_daily_time_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    time_text = (message.text or "").strip()
    if not TIME_REGEX.match(time_text):
        await message.answer("⚠️ Format waktu tidak valid. Gunakan format `HH:MM` (contoh: `21:00`):")
        return

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    pref = await ReportService.get_or_create_preference(session, user.id)
    pref.daily_time = time_text
    await session.flush()
    await state.clear()

    await message.answer(
        f"✅ Jam laporan harian berhasil diatur ke pukul *{time_text} WIB*.",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(pref),
    )


@router.callback_query(F.data == "set:time:weekly")
async def prompt_weekly_day_and_time(
    callback: CallbackQuery, state: FSMContext
) -> None:
    days = [
        ("Senin", 0),
        ("Selasa", 1),
        ("Rabu", 2),
        ("Kamis", 3),
        ("Jumat", 4),
        ("Sabtu", 5),
        ("Minggu", 6),
    ]
    rows = []
    for day_name, day_idx in days:
        rows.append([InlineKeyboardButton(text=day_name, callback_data=f"set:wday:{day_idx}")])
    rows.append([InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")])

    await state.set_state(SettingsState.waiting_for_weekly_day)
    await callback.message.edit_text(
        "📅 *ATUR HARI PENGIRIMAN MINGGUAN*\n\n"
        "Silakan pilih hari dalam sepekan:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(
    SettingsState.waiting_for_weekly_day, F.data.startswith("set:wday:")
)
async def handle_weekly_day_picked(
    callback: CallbackQuery, state: FSMContext
) -> None:
    wday = int(callback.data.split(":")[2])
    await state.update_data(weekly_day=wday)
    await state.set_state(SettingsState.waiting_for_weekly_time)

    days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    await callback.message.edit_text(
        f"📅 Hari Dipilih: *{days_id[wday]}*\n\n"
        "Sekarang masukkan *jam pengiriman* dalam format 24-jam `HH:MM` WIB (contoh: `21:00`):",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(SettingsState.waiting_for_weekly_time)
async def handle_weekly_time_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    time_text = (message.text or "").strip()
    if not TIME_REGEX.match(time_text):
        await message.answer("⚠️ Format waktu tidak valid. Gunakan format `HH:MM` (contoh: `21:00`):")
        return

    data = await state.get_data()
    wday = data.get("weekly_day", 6)

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    pref = await ReportService.get_or_create_preference(session, user.id)
    pref.weekly_day = wday
    pref.weekly_time = time_text
    await session.flush()
    await state.clear()

    days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    await message.answer(
        f"✅ Jadwal laporan mingguan berhasil diatur ke hari *{days_id[wday]}* pukul *{time_text} WIB*.",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(pref),
    )


@router.callback_query(F.data == "set:time:monthly")
async def prompt_monthly_time(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.set_state(SettingsState.waiting_for_monthly_time)
    await callback.message.edit_text(
        "⏱ *ATUR JAM LAPORAN BULANAN*\n\n"
        "Laporan bulanan dikirim pada hari kalender terakhir setiap bulan.\n"
        "Masukkan jam pengiriman dalam format 24-jam `HH:MM` WIB (contoh: `21:00`):",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(SettingsState.waiting_for_monthly_time)
async def handle_monthly_time_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    time_text = (message.text or "").strip()
    if not TIME_REGEX.match(time_text):
        await message.answer("⚠️ Format waktu tidak valid. Gunakan format `HH:MM` (contoh: `21:00`):")
        return

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    pref = await ReportService.get_or_create_preference(session, user.id)
    pref.monthly_time = time_text
    await session.flush()
    await state.clear()

    await message.answer(
        f"✅ Jam laporan bulanan berhasil diatur ke pukul *{time_text} WIB* pada akhir bulan.",
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(pref),
    )

