"""Dashboard handler showing balances, income, expense, and recent transactions."""

import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_DASHBOARD, TransactionType, format_idr
from app.core.timezone import format_date_id
from app.keyboards.reply_keyboards import get_main_menu_keyboard
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="dashboard_router")


async def render_dashboard_text(session: AsyncSession, telegram_user_id: int) -> str:
    """Build formatted dashboard text."""
    user = await UserService.get_by_telegram_id(session, telegram_user_id)
    if not user:
        return "⚠️ Data akun belum ditemukan. Silakan ketik /start untuk mendaftar."

    summary = await TransactionService.get_financial_summary(session, user.id)

    lines = [
        "📊 *DASHBOARD KEUANGAN*",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Saldo Saat Ini:* `{format_idr(summary['current_balance'])}`",
        f"🟢 *Total Pemasukan:* `{format_idr(summary['total_income'])}`",
        f"🔴 *Total Pengeluaran:* `{format_idr(summary['total_expense'])}`",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "🕒 *Transaksi Terakhir:*",
    ]

    recent_txs = summary["recent_transactions"]
    if not recent_txs:
        lines.append(" • _Belum ada transaksi tercatat (Saldo awal Rp0)._")
    else:
        for tx in recent_txs:
            emoji = "🟢" if tx.transaction_type == TransactionType.PEMASUKAN.value else "🔴"
            cat_name = tx.category.name if tx.category else "-"
            date_str = format_date_id(tx.transaction_date)
            note_str = f" _({tx.note})_" if tx.note else ""
            lines.append(
                f"{emoji} `{date_str}`: *{cat_name}* • `{format_idr(tx.amount)}`{note_str}"
            )

    return "\n".join(lines)


@router.message(F.text == BTN_DASHBOARD)
@router.message(Command("dashboard"))
async def show_dashboard(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Show the financial dashboard."""
    await state.clear()
    text = await render_dashboard_text(session, message.from_user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Segarkan Dashboard", callback_data="dash:refresh")]
        ]
    )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "dash:refresh")
async def refresh_dashboard(callback: CallbackQuery, session: AsyncSession) -> None:
    """Refresh the dashboard view."""
    text = await render_dashboard_text(session, callback.from_user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Segarkan Dashboard", callback_data="dash:refresh")]
        ]
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        await callback.answer("Dashboard diperbarui!")
    except Exception:
        await callback.answer("Dashboard sudah terkini.")

