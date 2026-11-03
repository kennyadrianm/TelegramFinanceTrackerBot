"""Multi-step Add Transaction workflow handler."""

from datetime import date, datetime
import logging
import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_ADD_TX, TransactionType, format_idr
from app.core.timezone import (
    format_date_id,
    format_date_long_id,
    parse_date_str,
    today_wib,
)
from app.keyboards.calendar_keyboard import create_calendar
from app.keyboards.inline_keyboards import (
    get_category_picker_keyboard,
    get_date_option_keyboard,
    get_fix_field_keyboard,
    get_skip_note_keyboard,
    get_transaction_confirm_keyboard,
    get_transaction_type_keyboard,
)
from app.keyboards.reply_keyboards import get_main_menu_keyboard
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService
from app.states.form_states import AddTransactionState

logger = logging.getLogger(__name__)
router = Router(name="transaction_add_router")


def parse_rupiah_input(text: str) -> int | None:
    """Parse user text input into a positive integer Rupiah value.
    
    Accepts:
        '50000' -> 50000
        '50.000' -> 50000
        'Rp 50.000' -> 50000
        'rp50000' -> 50000
    Rejects:
        Decimals ('50.50'), negative values, non-numeric strings, 0.
    """
    clean = text.strip().lower()
    if clean.startswith("rp"):
        clean = clean[2:].strip()

    # Reject if comma decimal or point decimal is entered as fractional cents
    # Note: in Indonesian number notation, '.' is thousands separator.
    # If user writes '50,5' or '50.50' it's invalid.
    if "," in clean:
        # Check if comma is used as thousands or decimal
        parts = clean.split(",")
        if len(parts) == 2 and len(parts[1]) != 3:
            return None  # decimal fractional not allowed

    # Remove standard thousands separators (dots)
    clean_digits = clean.replace(".", "").replace(",", "").replace(" ", "")
    if not clean_digits.isdigit():
        return None

    val = int(clean_digits)
    return val if val > 0 else None


async def render_transaction_preview(
    session: AsyncSession, user_id: int, data: dict
) -> str:
    """Format transaction preview for user confirmation."""
    tx_type = data.get("type", TransactionType.PENGELUARAN.value)
    type_label = "🟢 Pemasukan" if tx_type == TransactionType.PEMASUKAN.value else "🔴 Pengeluaran"
    amount = data.get("amount", 0)
    cat_id = data.get("category_id")
    cat = await CategoryService.get_by_id(session, user_id, cat_id) if cat_id else None
    cat_name = cat.name if cat else "-"

    date_val = data.get("date")
    if isinstance(date_val, str):
        tx_date = date.fromisoformat(date_val)
    elif isinstance(date_val, date):
        tx_date = date_val
    else:
        tx_date = today_wib()

    note_val = data.get("note") or "_(Tanpa catatan)_"

    preview = (
        "🔍 *KONFIRMASI TRANSAKSI*\n"
        "Mohon periksa kembali rincian transaksi Anda:\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Tipe Transaksi:* {type_label}\n"
        f"💰 *Nominal:* `{format_idr(amount)}`\n"
        f"🏷️ *Kategori:* *{cat_name}*\n"
        f"📅 *Tanggal:* {format_date_long_id(tx_date)} (`{format_date_id(tx_date)}`)\n"
        f"📝 *Catatan:* {note_val}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tekan *Simpan* untuk menyimpan ke pembukuan, *Perbaiki* untuk mengubah data, atau *Batalkan*."
    )
    return preview


# 1. Start Add Transaction
@router.message(F.text == BTN_ADD_TX)
@router.message(Command("tambah"))
async def start_add_transaction(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Step 1: Initiate transaction creation and prompt for type."""
    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Silakan mulai bot terlebih dahulu dengan mengetik /start")
        return

    await state.clear()
    await state.set_state(AddTransactionState.waiting_for_type)
    await message.answer(
        "➕ *Tambah Transaksi Baru*\n\n"
        "Silakan pilih jenis transaksi yang ingin dicatat:",
        parse_mode="Markdown",
        reply_markup=get_transaction_type_keyboard(prefix="tx:add_type"),
    )


# 2. Receive Type -> Prompt Amount
@router.callback_query(
    AddTransactionState.waiting_for_type, F.data.startswith("tx:add_type:")
)
async def handle_type_selected(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Step 2: Save selected type and ask for transaction amount."""
    tx_type = callback.data.split(":")[2]
    await state.update_data(type=tx_type)
    await state.set_state(AddTransactionState.waiting_for_amount)

    type_label = "Pemasukan" if tx_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    emoji = "🟢" if tx_type == TransactionType.PEMASUKAN.value else "🔴"

    await callback.message.edit_text(
        f"{emoji} *Jenis Transaksi:* *{type_label}*\n\n"
        "Silakan masukkan *nominal transaksi* dalam Rupiah (bilangan bulat positif):\n"
        "• Contoh: `50000` atau `50.000` atau `Rp 50.000`\n\n"
        "_(Ketik nominal melalui pesan chat di bawah atau /cancel untuk batal)_",
        parse_mode="Markdown",
    )
    await callback.answer()


# 3. Receive Amount -> Prompt Category
@router.message(AddTransactionState.waiting_for_amount)
async def handle_amount_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Step 3: Validate amount and prompt user to choose a category."""
    amount = parse_rupiah_input(message.text or "")
    if amount is None or amount <= 0:
        await message.answer(
            "⚠️ *Nominal Tidak Valid!*\n\n"
            "Harap masukkan nominal transaksi berupa angka bilangan bulat positif (contoh: `25000` atau `25.000`).\n"
            "Tidak diperkenankan menggunakan angka desimal, nol, atau angka negatif.\n\n"
            "Silakan ketik ulang nominal:",
            parse_mode="Markdown",
        )
        return

    data = await state.get_data()
    tx_type = data.get("type", TransactionType.PENGELUARAN.value)
    await state.update_data(amount=amount)
    await state.set_state(AddTransactionState.waiting_for_category)

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    categories = await CategoryService.get_categories(
        session, user.id, transaction_type=tx_type
    )

    type_label = "Pemasukan" if tx_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    await message.answer(
        f"💰 *Nominal:* `{format_idr(amount)}`\n\n"
        f"Silakan pilih *kategori {type_label.lower()}* yang sesuai:",
        parse_mode="Markdown",
        reply_markup=get_category_picker_keyboard(categories, prefix="tx:add_cat"),
    )


# 4. Receive Category -> Prompt Date
@router.callback_query(
    AddTransactionState.waiting_for_category, F.data.startswith("tx:add_cat:")
)
async def handle_category_selected(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Step 4: Save category and ask for transaction date."""
    cat_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    cat = await CategoryService.get_by_id(session, user.id, cat_id)

    if not cat:
        await callback.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    await state.update_data(category_id=cat_id)
    await state.set_state(AddTransactionState.waiting_for_date)

    today = today_wib()
    await callback.message.edit_text(
        f"🏷️ *Kategori:* *{cat.name}*\n\n"
        "🗓 *Tanggal Transaksi:*\n"
        f"Secara bawaan transaksi akan dicatat untuk hari ini (*{format_date_id(today)}*).\n\n"
        "Anda dapat menggunakan hari ini, membuka kalender interaktif, atau mengetik tanggal manual dalam format `DD-MM-YYYY` (contoh: `25-10-2026`):",
        parse_mode="Markdown",
        reply_markup=get_date_option_keyboard(),
    )
    await callback.answer()


# 5. Date selection handlers (Today button, Calendar button, Calendar Navigation/Date, or Manual Text)
@router.callback_query(
    AddTransactionState.waiting_for_date, F.data == "tx:date:today"
)
@router.callback_query(
    AddTransactionState.waiting_for_date, F.data == "cal:today"
)
async def handle_date_today(callback: CallbackQuery, state: FSMContext) -> None:
    """Use today's date in Asia/Jakarta."""
    today = today_wib()
    await state.update_data(date=today.isoformat())
    await state.set_state(AddTransactionState.waiting_for_note)

    await callback.message.edit_text(
        f"📅 *Tanggal Dipilih:* *{format_date_long_id(today)}* (`{format_date_id(today)}`)\n\n"
        "📝 *Catatan Transaksi (Opsional):*\n"
        "Ketik catatan singkat untuk transaksi ini (misal: 'Makan siang bareng teman'), "
        "atau tekan tombol di bawah untuk melewati:",
        parse_mode="Markdown",
        reply_markup=get_skip_note_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_date, F.data == "tx:date:calendar"
)
async def handle_open_calendar(callback: CallbackQuery) -> None:
    """Display the interactive calendar."""
    today = today_wib()
    await callback.message.edit_text(
        "🗓 *Pilih Tanggal Transaksi:*\n"
        "Gunakan panah ◀️ / ▶️ untuk navigasi bulan, lalu klik angka tanggal.",
        parse_mode="Markdown",
        reply_markup=create_calendar(today.year, today.month),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_date, F.data.startswith("cal:nav:")
)
async def handle_calendar_nav(callback: CallbackQuery) -> None:
    """Handle month navigation in inline calendar."""
    parts = callback.data.split(":")
    year, month = int(parts[2]), int(parts[3])
    await callback.message.edit_reply_markup(reply_markup=create_calendar(year, month))
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_date, F.data.startswith("cal:date:")
)
async def handle_calendar_date_picked(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle clicking a specific date on the inline calendar."""
    date_str = callback.data.split(":")[2]
    picked_date = date.fromisoformat(date_str)
    await state.update_data(date=picked_date.isoformat())
    await state.set_state(AddTransactionState.waiting_for_note)

    await callback.message.edit_text(
        f"📅 *Tanggal Dipilih:* *{format_date_long_id(picked_date)}* (`{format_date_id(picked_date)}`)\n\n"
        "📝 *Catatan Transaksi (Opsional):*\n"
        "Ketik catatan transaksi Anda di bawah, atau tekan tombol untuk melewati:",
        parse_mode="Markdown",
        reply_markup=get_skip_note_keyboard(),
    )
    await callback.answer()


@router.message(AddTransactionState.waiting_for_date)
async def handle_manual_date_input(message: Message, state: FSMContext) -> None:
    """Handle manual date input in DD-MM-YYYY format."""
    parsed = parse_date_str(message.text or "")
    if not parsed:
        await message.answer(
            "⚠️ *Format Tanggal Tidak Valid!*\n\n"
            "Format yang diterima adalah `DD-MM-YYYY` (contoh: `25-10-2026`).\n"
            "Silakan ketik ulang atau pilih tanggal menggunakan tombol di atas:",
            parse_mode="Markdown",
        )
        return

    await state.update_data(date=parsed.isoformat())
    await state.set_state(AddTransactionState.waiting_for_note)
    await message.answer(
        f"📅 *Tanggal Dipilih:* *{format_date_long_id(parsed)}* (`{format_date_id(parsed)}`)\n\n"
        "📝 *Catatan Transaksi (Opsional):*\n"
        "Ketik catatan transaksi Anda di bawah, atau tekan tombol untuk melewati:",
        parse_mode="Markdown",
        reply_markup=get_skip_note_keyboard(),
    )


# 6. Note input handlers (Skip or Text message)
@router.callback_query(
    AddTransactionState.waiting_for_note, F.data == "tx:note:skip"
)
async def handle_note_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Skip transaction note and show preview."""
    await state.update_data(note=None)
    await state.set_state(AddTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    preview = await render_transaction_preview(session, user.id, data)

    await callback.message.edit_text(
        preview,
        parse_mode="Markdown",
        reply_markup=get_transaction_confirm_keyboard(),
    )
    await callback.answer()


@router.message(AddTransactionState.waiting_for_note)
async def handle_note_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Save user note and show preview."""
    note_text = message.text.strip() if message.text else ""
    if len(note_text) > 500:
        await message.answer("Catatan maksimal 500 karakter. Silakan ketik catatan yang lebih ringkas:")
        return

    await state.update_data(note=note_text if note_text else None)
    await state.set_state(AddTransactionState.waiting_for_confirmation)

    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    data = await state.get_data()
    preview = await render_transaction_preview(session, user.id, data)

    await message.answer(
        preview,
        parse_mode="Markdown",
        reply_markup=get_transaction_confirm_keyboard(),
    )


# 7. Confirmation actions: Save, Fix, or Cancel
@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:confirm:save"
)
async def handle_confirm_save(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Step 7: Explicit confirmation - persist transaction to database."""
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()

    tx_type = data["type"]
    amount = data["amount"]
    category_id = data["category_id"]
    date_val = data.get("date")
    tx_date = date.fromisoformat(date_val) if date_val else today_wib()
    note = data.get("note")

    tx, err = await TransactionService.create_transaction(
        session=session,
        user_id=user.id,
        category_id=category_id,
        transaction_type=tx_type,
        amount=amount,
        transaction_date=tx_date,
        note=note,
    )

    if err:
        await callback.answer(f"Gagal menyimpan: {err}", show_alert=True)
        return

    summary = await TransactionService.get_financial_summary(session, user.id)
    await state.clear()

    type_label = "Pemasukan" if tx_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    emoji = "🟢" if tx_type == TransactionType.PEMASUKAN.value else "🔴"

    success_msg = (
        f"✅ *Transaksi Berhasil Disimpan!*\n\n"
        f"{emoji} *{type_label}:* `{format_idr(amount)}`\n"
        f"🏷️ *Kategori:* *{tx.category.name}*\n"
        f"📅 *Tanggal:* `{format_date_id(tx.transaction_date)}`\n"
        f"📝 *Catatan:* {tx.note or '_(Tanpa catatan)_'}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Saldo Terkini:* `{format_idr(summary['current_balance'])}`"
    )

    try:
        await callback.message.edit_text(success_msg, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(success_msg, parse_mode="Markdown")

    await callback.answer("Transaksi berhasil disimpan!")


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:confirm:fix"
)
async def handle_confirm_fix(callback: CallbackQuery) -> None:
    """Allow user to select which field to fix/update."""
    await callback.message.edit_text(
        "✏️ *Pilih bagian transaksi yang ingin diperbaiki:*",
        parse_mode="Markdown",
        reply_markup=get_fix_field_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:fix:back"
)
async def handle_fix_back(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Return to preview confirmation from fix menu."""
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    data = await state.get_data()
    preview = await render_transaction_preview(session, user.id, data)
    await callback.message.edit_text(
        preview,
        parse_mode="Markdown",
        reply_markup=get_transaction_confirm_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:fix:type"
)
async def handle_fix_type(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddTransactionState.waiting_for_type)
    await callback.message.edit_text(
        "Pilih jenis transaksi yang baru:",
        reply_markup=get_transaction_type_keyboard(prefix="tx:add_type"),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:fix:amount"
)
async def handle_fix_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddTransactionState.waiting_for_amount)
    await callback.message.edit_text(
        "Ketik nominal transaksi yang baru (contoh: `75000` atau `75.000`):"
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:fix:category"
)
async def handle_fix_category(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    categories = await CategoryService.get_categories(
        session, user.id, transaction_type=data.get("type")
    )
    await state.set_state(AddTransactionState.waiting_for_category)
    await callback.message.edit_text(
        "Pilih kategori yang baru:",
        reply_markup=get_category_picker_keyboard(categories, prefix="tx:add_cat"),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:fix:date"
)
async def handle_fix_date(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddTransactionState.waiting_for_date)
    await callback.message.edit_text(
        "Pilih atau ketik tanggal transaksi yang baru (DD-MM-YYYY):",
        reply_markup=get_date_option_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    AddTransactionState.waiting_for_confirmation, F.data == "tx:fix:note"
)
async def handle_fix_note(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddTransactionState.waiting_for_note)
    await callback.message.edit_text(
        "Ketik catatan transaksi yang baru atau tekan tombol untuk melewati:",
        reply_markup=get_skip_note_keyboard(),
    )
    await callback.answer()

