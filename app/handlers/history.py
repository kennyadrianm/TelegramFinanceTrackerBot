"""Transaction history handler with pagination, filters, and item inspection."""

import math
from datetime import date
import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_HISTORY, TransactionType, format_idr
from app.core.timezone import (
    format_date_id,
    format_date_long_id,
    get_month_range,
    get_week_range,
    today_wib,
)
from app.keyboards.inline_keyboards import (
    get_history_navigation_keyboard,
    get_transaction_detail_keyboard,
)
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="history_router")

PAGE_SIZE = 5


async def fetch_history_page(
    session: AsyncSession,
    user_id: int,
    page: int = 1,
    filter_type: str | None = None,
    filter_period: str | None = "ALL",
) -> tuple[str, InlineKeyboardMarkup]:
    """Fetch paginated transactions and render list view."""
    today = today_wib()
    start_date = None
    end_date = None

    if filter_period == "TODAY":
        start_date, end_date = today, today
    elif filter_period == "THIS_WEEK":
        start_date, end_date = get_week_range(today)
    elif filter_period == "THIS_MONTH":
        start_date, end_date = get_month_range(today)

    offset = (page - 1) * PAGE_SIZE
    txs, total_count = await TransactionService.get_transactions(
        session=session,
        user_id=user_id,
        transaction_type=filter_type,
        start_date=start_date,
        end_date=end_date,
        limit=PAGE_SIZE,
        offset=offset,
    )

    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))

    # Header title
    type_str = ""
    if filter_type == TransactionType.PEMASUKAN.value:
        type_str = " (🟢 Pemasukan)"
    elif filter_type == TransactionType.PENGELUARAN.value:
        type_str = " (🔴 Pengeluaran)"

    period_str = {
        "ALL": "Semua Waktu",
        "TODAY": "Hari Ini",
        "THIS_WEEK": "Minggu Ini",
        "THIS_MONTH": "Bulan Ini",
    }.get(filter_period or "ALL", "Semua Waktu")

    lines = [
        f"📜 *RIWAYAT TRANSAKSI*{type_str}",
        f"🗓 *Periode:* {period_str}",
        f"🔢 *Total Data:* {total_count} transaksi",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    tx_buttons_data: list[tuple[int, str]] = []

    if not txs:
        lines.append("\n_Belum ada transaksi pada kriteria filter ini._")
    else:
        for idx, tx in enumerate(txs, start=offset + 1):
            is_inc = tx.transaction_type == TransactionType.PEMASUKAN.value
            emoji = "🟢" if is_inc else "🔴"
            cat_name = tx.category.name if tx.category else "-"
            date_str = format_date_id(tx.transaction_date)
            note_str = f" • _{tx.note}_" if tx.note else ""
            lines.append(
                f"{idx}. {emoji} `{date_str}`: *{cat_name}* • `{format_idr(tx.amount)}`{note_str}"
            )
            btn_label = f"Lihat #{idx} ({date_str} - {cat_name})"
            tx_buttons_data.append((tx.id, btn_label))

    keyboard = get_history_navigation_keyboard(page, total_pages, tx_buttons_data)
    return "\n".join(lines), keyboard


@router.message(F.text == BTN_HISTORY)
@router.message(Command("riwayat"))
async def show_history(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Entry point for transaction history."""
    await state.clear()
    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Silakan mulai bot dengan /start.")
        return

    # Store default filter state in FSM
    await state.update_data(
        hist_page=1,
        hist_type=None,
        hist_period="ALL",
    )

    text, kb = await fetch_history_page(session, user.id, page=1)
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data.startswith("history:page:"))
async def handle_history_page_turn(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Handle pagination page change."""
    page = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()

    filter_type = data.get("hist_type")
    filter_period = data.get("hist_period", "ALL")
    await state.update_data(hist_page=page)

    text, kb = await fetch_history_page(
        session, user.id, page=page, filter_type=filter_type, filter_period=filter_period
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "history:filters")
async def show_history_filters(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Display filter controls for history."""
    data = await state.get_data()
    active_type = data.get("hist_type")
    active_period = data.get("hist_period", "ALL")

    from app.keyboards.inline_keyboards import get_history_filter_keyboard

    await callback.message.edit_text(
        "🔍 *PENGATURAN FILTER RIWAYAT*\n\n"
        "Klik tombol di bawah untuk mengganti kriteria penyaringan:",
        parse_mode="Markdown",
        reply_markup=get_history_filter_keyboard(active_type, active_period),
    )
    await callback.answer()


@router.callback_query(F.data == "hist_fil:toggle_type")
async def toggle_filter_type(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Cycle filter type: ALL -> PEMASUKAN -> PENGELUARAN -> ALL."""
    data = await state.get_data()
    current = data.get("hist_type")

    if current is None:
        new_type = TransactionType.PEMASUKAN.value
    elif current == TransactionType.PEMASUKAN.value:
        new_type = TransactionType.PENGELUARAN.value
    else:
        new_type = None

    await state.update_data(hist_type=new_type)
    data = await state.get_data()

    from app.keyboards.inline_keyboards import get_history_filter_keyboard

    await callback.message.edit_reply_markup(
        reply_markup=get_history_filter_keyboard(new_type, data.get("hist_period", "ALL"))
    )
    await callback.answer()


@router.callback_query(F.data == "hist_fil:toggle_period")
async def toggle_filter_period(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Cycle period: ALL -> TODAY -> THIS_WEEK -> THIS_MONTH -> ALL."""
    data = await state.get_data()
    current = data.get("hist_period", "ALL")

    cycle = ["ALL", "TODAY", "THIS_WEEK", "THIS_MONTH"]
    next_idx = (cycle.index(current) + 1) % len(cycle) if current in cycle else 0
    new_period = cycle[next_idx]

    await state.update_data(hist_period=new_period)
    data = await state.get_data()

    from app.keyboards.inline_keyboards import get_history_filter_keyboard

    await callback.message.edit_reply_markup(
        reply_markup=get_history_filter_keyboard(data.get("hist_type"), new_period)
    )
    await callback.answer()


@router.callback_query(F.data == "hist_fil:reset")
async def reset_history_filters(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Reset history filters to all."""
    await state.update_data(hist_type=None, hist_period="ALL", hist_page=1)
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    text, kb = await fetch_history_page(session, user.id, page=1)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer("Filter direset ke semua waktu.")


@router.callback_query(F.data.startswith("tx:view:"))
async def view_transaction_detail(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Display individual transaction detail with Edit and Delete action buttons."""
    tx_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    tx = await TransactionService.get_by_id(session, user.id, tx_id)

    if not tx:
        await callback.answer("Transaksi tidak ditemukan.", show_alert=True)
        return

    is_inc = tx.transaction_type == TransactionType.PEMASUKAN.value
    type_label = "🟢 Pemasukan" if is_inc else "🔴 Pengeluaran"
    cat_name = tx.category.name if tx.category else "-"
    date_str = format_date_long_id(tx.transaction_date)

    detail_text = (
        "📄 *RINCIAN TRANSAKSI*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Tipe:* {type_label}\n"
        f"💰 *Nominal:* `{format_idr(tx.amount)}`\n"
        f"🏷️ *Kategori:* *{cat_name}*\n"
        f"📅 *Tanggal:* {date_str} (`{format_date_id(tx.transaction_date)}`)\n"
        f"📝 *Catatan:* {tx.note or '_(Tanpa catatan)_'}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Pilih tindakan untuk transaksi ini:"
    )

    await callback.message.edit_text(
        detail_text,
        parse_mode="Markdown",
        reply_markup=get_transaction_detail_keyboard(tx.id),
    )
    await callback.answer()


@router.callback_query(F.data == "history:back")
async def handle_history_back(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Return to the history list from detail view."""
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    page = data.get("hist_page", 1)
    filter_type = data.get("hist_type")
    filter_period = data.get("hist_period", "ALL")

    text, kb = await fetch_history_page(
        session, user.id, page=page, filter_type=filter_type, filter_period=filter_period
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

