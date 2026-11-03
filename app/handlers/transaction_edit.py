"""Transaction editing handler with field selection, category compatibility checks, and preview."""

from datetime import date
import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType, format_idr
from app.core.timezone import (
    format_date_id,
    format_date_long_id,
    parse_date_str,
    today_wib,
)
from app.handlers.transaction_add import parse_rupiah_input
from app.keyboards.calendar_keyboard import create_calendar
from app.keyboards.inline_keyboards import (
    get_category_picker_keyboard,
    get_date_option_keyboard,
    get_skip_note_keyboard,
    get_transaction_type_keyboard,
)
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService
from app.states.form_states import EditTransactionState

logger = logging.getLogger(__name__)
router = Router(name="transaction_edit_router")


def get_edit_menu_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    """Keyboard for selecting which field to edit."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Tipe Transaksi", callback_data=f"tx:edit_field:{tx_id}:type"),
                InlineKeyboardButton(text="💰 Nominal", callback_data=f"tx:edit_field:{tx_id}:amount"),
            ],
            [
                InlineKeyboardButton(text="🏷️ Kategori", callback_data=f"tx:edit_field:{tx_id}:category"),
                InlineKeyboardButton(text="📅 Tanggal", callback_data=f"tx:edit_field:{tx_id}:date"),
            ],
            [
                InlineKeyboardButton(text="📝 Catatan", callback_data=f"tx:edit_field:{tx_id}:note"),
            ],
            [InlineKeyboardButton(text="❌ Batalkan Pengeditan", callback_data="action:cancel")],
        ]
    )


def get_edit_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation buttons for applying edits."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💾 Simpan Perubahan", callback_data="tx:edit_save"),
                InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel"),
            ]
        ]
    )


async def render_edit_preview(session: AsyncSession, user_id: int, data: dict) -> str:
    """Format changes preview before saving."""
    tx_id = data["tx_id"]
    tx = await TransactionService.get_by_id(session, user_id, tx_id)
    if not tx:
        return "Transaksi tidak ditemukan."

    new_type = data.get("new_type", tx.transaction_type)
    new_amount = data.get("new_amount", tx.amount)
    new_cat_id = data.get("new_category_id", tx.category_id)
    new_cat = await CategoryService.get_by_id(session, user_id, new_cat_id)
    new_cat_name = new_cat.name if new_cat else "-"

    new_date_val = data.get("new_date")
    if isinstance(new_date_val, str):
        new_date = date.fromisoformat(new_date_val)
    elif isinstance(new_date_val, date):
        new_date = new_date_val
    else:
        new_date = tx.transaction_date

    new_note = data.get("new_note", tx.note)

    type_label = "🟢 Pemasukan" if new_type == TransactionType.PEMASUKAN.value else "🔴 Pengeluaran"

    preview = (
        "🔍 *PREVIEW PERUBAHAN TRANSAKSI*\n"
        "Silakan periksa kembali data hasil perubahan:\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Tipe:* {type_label}\n"
        f"💰 *Nominal:* `{format_idr(new_amount)}`\n"
        f"🏷️ *Kategori:* *{new_cat_name}*\n"
        f"📅 *Tanggal:* {format_date_long_id(new_date)} (`{format_date_id(new_date)}`)\n"
        f"📝 *Catatan:* {new_note or '_(Tanpa catatan)_'}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tekan *Simpan Perubahan* untuk memperbarui data."
    )
    return preview


# 1. Initialize Edit
@router.callback_query(F.data.startswith("tx:edit_init:"))
async def init_edit_transaction(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Start transaction edit flow and present editable fields."""
    tx_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    tx = await TransactionService.get_by_id(session, user.id, tx_id)

    if not tx:
        await callback.answer("Transaksi tidak ditemukan.", show_alert=True)
        return

    await state.clear()
    await state.set_state(EditTransactionState.waiting_for_field_selection)
    await state.update_data(
        tx_id=tx.id,
        current_type=tx.transaction_type,
        current_amount=tx.amount,
        current_category_id=tx.category_id,
        current_date=tx.transaction_date.isoformat(),
        current_note=tx.note,
    )

    type_label = "Pemasukan" if tx.transaction_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    cat_name = tx.category.name if tx.category else "-"

    text = (
        "✏️ *UBAH TRANSAKSI*\n\n"
        f"📌 *Tipe Saat Ini:* {type_label}\n"
        f"💰 *Nominal:* `{format_idr(tx.amount)}`\n"
        f"🏷️ *Kategori:* *{cat_name}*\n"
        f"📅 *Tanggal:* `{format_date_id(tx.transaction_date)}`\n"
        f"📝 *Catatan:* {tx.note or '-(Tanpa catatan)-'}\n\n"
        "Pilih bagian yang ingin Anda ubah:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_edit_menu_keyboard(tx.id),
    )
    await callback.answer()


# 2. Field Selection Handlers
@router.callback_query(
    EditTransactionState.waiting_for_field_selection,
    F.data.startswith("tx:edit_field:"),
)
async def handle_edit_field_pick(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    parts = callback.data.split(":")
    tx_id, field = int(parts[2]), parts[3]
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()

    if field == "type":
        await state.set_state(EditTransactionState.waiting_for_new_type)
        await callback.message.edit_text(
            "Pilih tipe transaksi yang baru:",
            reply_markup=get_transaction_type_keyboard(prefix="tx:edit_type"),
        )
    elif field == "amount":
        await state.set_state(EditTransactionState.waiting_for_new_amount)
        await callback.message.edit_text(
            "Silakan ketik nominal transaksi baru dalam Rupiah (contoh: `100000` atau `100.000`):"
        )
    elif field == "category":
        await state.set_state(EditTransactionState.waiting_for_new_category)
        tx_type = data.get("new_type", data.get("current_type"))
        cats = await CategoryService.get_categories(session, user.id, transaction_type=tx_type)
        await callback.message.edit_text(
            "Pilih kategori baru:",
            reply_markup=get_category_picker_keyboard(cats, prefix="tx:edit_cat"),
        )
    elif field == "date":
        await state.set_state(EditTransactionState.waiting_for_new_date)
        await callback.message.edit_text(
            "Pilih tanggal transaksi baru atau ketik `DD-MM-YYYY`:",
            reply_markup=get_date_option_keyboard(),
        )
    elif field == "note":
        await state.set_state(EditTransactionState.waiting_for_new_note)
        await callback.message.edit_text(
            "Ketik catatan baru atau lewati untuk mengosongkan:",
            reply_markup=get_skip_note_keyboard(),
        )
    await callback.answer()


# 3. Handle New Type
@router.callback_query(
    EditTransactionState.waiting_for_new_type, F.data.startswith("tx:edit_type:")
)
async def handle_edit_type_selected(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    new_type = callback.data.split(":")[2]
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()

    # Category compatibility check: does current/new category match new_type?
    cat_id = data.get("new_category_id", data.get("current_category_id"))
    cat = await CategoryService.get_by_id(session, user.id, cat_id)

    await state.update_data(new_type=new_type)

    if not cat or cat.transaction_type != new_type:
        # Category incompatible! Force user to pick a category of the new type
        await state.set_state(EditTransactionState.waiting_for_new_category)
        cats = await CategoryService.get_categories(session, user.id, transaction_type=new_type)
        await callback.message.edit_text(
            f"⚠️ Tipe diubah menjadi *{'Pemasukan' if new_type == TransactionType.PEMASUKAN.value else 'Pengeluaran'}*.\n"
            f"Kategori sebelumnya tidak kompatibel. Silakan pilih kategori baru:",
            parse_mode="Markdown",
            reply_markup=get_category_picker_keyboard(cats, prefix="tx:edit_cat"),
        )
    else:
        # Compatible, proceed to preview
        await state.set_state(EditTransactionState.waiting_for_confirmation)
        data = await state.get_data()
        preview = await render_edit_preview(session, user.id, data)
        await callback.message.edit_text(
            preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
        )
    await callback.answer()


# 4. Handle New Amount
@router.message(EditTransactionState.waiting_for_new_amount)
async def handle_edit_amount_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    val = parse_rupiah_input(message.text or "")
    if val is None or val <= 0:
        await message.answer(
            "⚠️ Nominal tidak valid. Masukkan angka bulat positif lebih besar dari Rp0:"
        )
        return

    await state.update_data(new_amount=val)
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await message.answer(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )


# 5. Handle New Category
@router.callback_query(
    EditTransactionState.waiting_for_new_category, F.data.startswith("tx:edit_cat:")
)
async def handle_edit_cat_selected(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    cat_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    cat = await CategoryService.get_by_id(session, user.id, cat_id)

    if not cat:
        await callback.answer("Kategori tidak valid.", show_alert=True)
        return

    await state.update_data(new_category_id=cat_id)
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await callback.message.edit_text(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )
    await callback.answer()


# 6. Handle New Date
@router.callback_query(
    EditTransactionState.waiting_for_new_date, F.data == "tx:date:today"
)
async def handle_edit_date_today(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    today = today_wib()
    await state.update_data(new_date=today.isoformat())
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await callback.message.edit_text(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )
    await callback.answer()


@router.callback_query(
    EditTransactionState.waiting_for_new_date, F.data == "tx:date:calendar"
)
async def handle_edit_open_cal(callback: CallbackQuery) -> None:
    today = today_wib()
    await callback.message.edit_text(
        "Pilih tanggal:",
        reply_markup=create_calendar(today.year, today.month),
    )
    await callback.answer()


@router.callback_query(
    EditTransactionState.waiting_for_new_date, F.data.startswith("cal:nav:")
)
async def handle_edit_cal_nav(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    year, month = int(parts[2]), int(parts[3])
    await callback.message.edit_reply_markup(reply_markup=create_calendar(year, month))
    await callback.answer()


@router.callback_query(
    EditTransactionState.waiting_for_new_date, F.data.startswith("cal:date:")
)
async def handle_edit_cal_date(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    date_str = callback.data.split(":")[2]
    await state.update_data(new_date=date_str)
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await callback.message.edit_text(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )
    await callback.answer()


@router.message(EditTransactionState.waiting_for_new_date)
async def handle_edit_manual_date(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    parsed = parse_date_str(message.text or "")
    if not parsed:
        await message.answer("Format tanggal salah. Gunakan DD-MM-YYYY (contoh: 25-10-2026):")
        return

    await state.update_data(new_date=parsed.isoformat())
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await message.answer(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )


# 7. Handle New Note
@router.callback_query(
    EditTransactionState.waiting_for_new_note, F.data == "tx:note:skip"
)
async def handle_edit_note_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(new_note="", clear_note=True)
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await callback.message.edit_text(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )
    await callback.answer()


@router.message(EditTransactionState.waiting_for_new_note)
async def handle_edit_note_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    text = (message.text or "").strip()
    await state.update_data(new_note=text, clear_note=False)
    await state.set_state(EditTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    data = await state.get_data()
    preview = await render_edit_preview(session, user.id, data)
    await message.answer(
        preview, parse_mode="Markdown", reply_markup=get_edit_confirm_keyboard()
    )


# 8. Save Changes
@router.callback_query(
    EditTransactionState.waiting_for_confirmation, F.data == "tx:edit_save"
)
async def handle_save_edited_tx(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    tx_id = data["tx_id"]

    new_type = data.get("new_type")
    new_amount = data.get("new_amount")
    new_cat_id = data.get("new_category_id")
    new_date_val = data.get("new_date")
    new_date = date.fromisoformat(new_date_val) if new_date_val else None
    clear_note = data.get("clear_note", False)
    new_note = data.get("new_note")

    tx, err = await TransactionService.update_transaction(
        session=session,
        user_id=user.id,
        transaction_id=tx_id,
        category_id=new_cat_id,
        transaction_type=new_type,
        amount=new_amount,
        transaction_date=new_date,
        note=new_note,
        clear_note=clear_note,
    )

    if err:
        await callback.answer(f"Gagal memperbarui: {err}", show_alert=True)
        return

    await state.clear()
    summary = await TransactionService.get_financial_summary(session, user.id)

    msg = (
        "✅ *Perubahan Transaksi Berhasil Disimpan!*\n\n"
        f"💰 *Saldo Terkini:* `{format_idr(summary['current_balance'])}`"
    )

    try:
        await callback.message.edit_text(msg, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(msg, parse_mode="Markdown")

    await callback.answer("Transaksi berhasil diperbarui!")

