"""Transaction deletion handler with explicit confirmation."""

import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType, format_idr
from app.core.timezone import format_date_id
from app.keyboards.inline_keyboards import get_delete_confirmation_keyboard
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="transaction_delete_router")


@router.callback_query(F.data.startswith("tx:del_prompt:"))
async def prompt_delete_transaction(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Prompt user for explicit deletion confirmation showing transaction summary."""
    tx_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    tx = await TransactionService.get_by_id(session, user.id, tx_id)

    if not tx:
        await callback.answer("Transaksi tidak ditemukan.", show_alert=True)
        return

    type_label = "Pemasukan" if tx.transaction_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    cat_name = tx.category.name if tx.category else "-"
    date_str = format_date_id(tx.transaction_date)

    prompt_text = (
        "⚠️ *KONFIRMASI PENGHAPUSAN TRANSAKSI*\n\n"
        "Apakah Anda yakin ingin menghapus transaksi ini secara permanen?\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Tipe:* {type_label}\n"
        f"💰 *Nominal:* `{format_idr(tx.amount)}`\n"
        f"🏷️ *Kategori:* *{cat_name}*\n"
        f"📅 *Tanggal:* `{date_str}`\n"
        f"📝 *Catatan:* {tx.note or '-(Tanpa catatan)-'}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ _Tindakan ini tidak dapat dibatalkan._"
    )

    await callback.message.edit_text(
        prompt_text,
        parse_mode="Markdown",
        reply_markup=get_delete_confirmation_keyboard(tx.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tx:del_confirm:"))
async def confirm_delete_transaction(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Permanently delete transaction upon user confirmation."""
    tx_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)

    success, msg = await TransactionService.delete_transaction(session, user.id, tx_id)
    if not success:
        await callback.answer(f"Gagal menghapus: {msg}", show_alert=True)
        return

    summary = await TransactionService.get_financial_summary(session, user.id)

    result_text = (
        "🗑️ *Transaksi Telah Dihapus Permanen.*\n\n"
        f"💰 *Saldo Terkini:* `{format_idr(summary['current_balance'])}`\n\n"
        "Gunakan tombol menu di bawah untuk melanjutkan aktivitas pembukuan."
    )

    try:
        await callback.message.edit_text(result_text, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(result_text, parse_mode="Markdown")

    await callback.answer("Transaksi berhasil dihapus!")


@router.callback_query(F.data.startswith("tx:del_cancel:"))
async def cancel_delete_transaction(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Cancel deletion and return to transaction view."""
    await callback.answer("Penghapusan dibatalkan.")
    try:
        await callback.message.edit_text(
            "❌ Penghapusan transaksi dibatalkan.",
            reply_markup=None,
        )
    except Exception:
        pass

