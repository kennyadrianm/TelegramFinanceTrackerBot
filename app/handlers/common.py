"""Common bot handlers: /start, /help, /cancel, and general fallbacks."""

import logging
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import format_idr
from app.keyboards.reply_keyboards import get_main_menu_keyboard
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="common_router")


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Handle /start command, registering new users and presenting the dashboard."""
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    user, is_created = await UserService.get_or_create_user(
        session=session,
        telegram_user_id=user_id,
        username=username,
        first_name=first_name,
    )

    summary = await TransactionService.get_financial_summary(session, user.id)

    if is_created:
        welcome_prefix = (
            f"👋 *Selamat datang di Finance Tracker Bot, {first_name or 'Pengguna'}!*\n\n"
            "Akun Anda telah berhasil didaftarkan secara otomatis.\n"
            "Kategori bawaan dan preferensi laporan telah disiapkan.\n\n"
        )
    else:
        welcome_prefix = f"👋 *Halo kembali, {first_name or 'Pengguna'}!*\n\n"

    body = (
        f"{welcome_prefix}"
        "📊 *DASHBOARD KEUANGAN ANDA*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Saldo Saat Ini:* `{format_idr(summary['current_balance'])}`\n"
        f"🟢 *Total Pemasukan:* `{format_idr(summary['total_income'])}`\n"
        f"🔴 *Total Pengeluaran:* `{format_idr(summary['total_expense'])}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Gunakan menu di bawah untuk mulai mengelola keuangan Anda dengan mudah dan aman."
    )

    await message.answer(
        body,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("help"))
async def handle_help(message: Message, state: FSMContext) -> None:
    """Display help information and user guide."""
    await state.clear()
    help_text = (
        "💡 *PANDUAN PENGGUNAAN FINANCE TRACKER BOT*\n\n"
        "Bot ini membantu Anda mencatat dan memantau keuangan pribadi secara mandiri:\n\n"
        "📌 *Menu Utama:*\n"
        "• *📊 Dashboard:* Melihat ringkasan total saldo, pemasukan, dan pengeluaran.\n"
        "• *➕ Tambah Transaksi:* Mencatat pemasukan atau pengeluaran baru.\n"
        "• *📜 Riwayat:* Melihat daftar transaksi, memfilter, mengubah, atau menghapus.\n"
        "• *📈 Laporan:* Menampilkan laporan keuangan Harian, Mingguan, atau Bulanan.\n"
        "• *📁 Ekspor Data:* Mengunduh seluruh transaksi ke format CSV atau Excel (.xlsx).\n"
        "• *🏷️ Kelola Kategori:* Menambah, mengubah nama, atau menghapus kategori Anda.\n"
        "• *⚙️ Pengaturan:* Mengatur jadwal pengiriman laporan otomatis.\n\n"
        "🔒 *Keamanan & Privasi:*\n"
        "• Seluruh data transaksi diisolasi khusus untuk akun Telegram Anda.\n"
        "• Bot ini hanya dapat digunakan dalam pesan pribadi (Private Chat).\n"
        "• Ketik `/cancel` kapan saja untuk membatalkan proses yang sedang berjalan."
    )
    await message.answer(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("cancel"))
@router.message(F.text.casefold().in_(["batal", "batalkan", "/batal"]))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    """Cancel any active conversational state."""
    current_state = await state.get_state()
    await state.clear()
    msg = "❌ Proses telah dibatalkan." if current_state else "Tidak ada proses yang sedang berjalan."
    await message.answer(
        f"{msg}\n\nSilakan pilih menu di bawah:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data.in_(["action:cancel", "tx:confirm:cancel", "cal:cancel"]))
async def handle_inline_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle inline cancel buttons."""
    await state.clear()
    await callback.answer("Dibatalkan.")
    try:
        await callback.message.edit_text(
            "❌ Proses telah dibatalkan.\n\nSilakan gunakan menu di bawah untuk melanjutkan.",
            reply_markup=None,
        )
    except Exception:
        pass


@router.callback_query(F.data.in_(["action:ignore", "cal:ignore"]))
async def handle_ignore_callback(callback: CallbackQuery) -> None:
    """Ignore clicks on non-interactive headers or labels."""
    await callback.answer()

