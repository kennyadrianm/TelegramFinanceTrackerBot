"""Category management handlers: listing, adding custom, renaming, and deleting."""

import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_CATEGORIES, TransactionType
from app.keyboards.inline_keyboards import (
    get_categories_menu_keyboard,
    get_category_item_keyboard,
    get_transaction_type_keyboard,
)
from app.services.category_service import CategoryService
from app.services.user_service import UserService
from app.states.form_states import CategoryState

logger = logging.getLogger(__name__)
router = Router(name="category_router")


@router.message(F.text == BTN_CATEGORIES)
@router.message(Command("kategori"))
async def show_categories_menu(
    message: Message, state: FSMContext
) -> None:
    """Show the category management menu."""
    await state.clear()
    await message.answer(
        "🏷️ *KELOLA KATEGORI TRANSAKSI*\n\n"
        "Anda dapat melihat daftar kategori bawaan atau menambahkan kategori kustom Anda sendiri.\n\n"
        "Pilih tindakan:",
        parse_mode="Markdown",
        reply_markup=get_categories_menu_keyboard(),
    )


@router.callback_query(F.data == "cat:menu")
async def handle_cat_menu_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to category root menu."""
    await state.clear()
    await callback.message.edit_text(
        "🏷️ *KELOLA KATEGORI TRANSAKSI*\n\n"
        "Pilih kategori yang ingin Anda lihat atau buat kategori baru:",
        parse_mode="Markdown",
        reply_markup=get_categories_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:list:"))
async def list_categories_by_type(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show list of categories for Income or Expense."""
    tx_type = callback.data.split(":")[2]
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    cats = await CategoryService.get_categories(session, user.id, transaction_type=tx_type)

    type_label = "Pemasukan" if tx_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    emoji = "🟢" if tx_type == TransactionType.PEMASUKAN.value else "🔴"

    rows: list[list[InlineKeyboardButton]] = []
    for c in cats:
        badge = "🔒" if c.is_default else "⭐"
        label = f"{badge} {c.name}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"cat:inspect:{c.id}")])

    rows.append([InlineKeyboardButton(text="🔙 Kembali ke Menu Kategori", callback_data="cat:menu")])

    text = (
        f"{emoji} *DAFTAR KATEGORI {type_label.upper()}*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Keterangan:\n"
        "🔒 = Kategori Bawaan (Default)\n"
        "⭐ = Kategori Kustom Anda\n\n"
        "Klik kategori untuk melihat rincian atau mengubah/menghapus:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:inspect:"))
async def inspect_category(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Inspect category actions (Rename / Delete)."""
    cat_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    cat = await CategoryService.get_by_id(session, user.id, cat_id)

    if not cat:
        await callback.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    type_label = "Pemasukan" if cat.transaction_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    cat_kind = "Kategori Bawaan (Default)" if cat.is_default else "Kategori Kustom"

    text = (
        f"🏷️ *RINCIAN KATEGORI*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Nama:* *{cat.name}*\n"
        f"🔄 *Tipe:* {type_label}\n"
        f"🏷️ *Status:* {cat_kind}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Pilih tindakan untuk kategori ini:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_category_item_keyboard(cat.id, cat.is_default),
    )
    await callback.answer()


# --- Add Custom Category Flow ---
@router.callback_query(F.data == "cat:add:start")
async def start_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Start creating a custom category: ask for transaction type."""
    await state.set_state(CategoryState.waiting_for_type_selection)
    await callback.message.edit_text(
        "➕ *BUAT KATEGORI BARU*\n\n"
        "Pilih jenis transaksi untuk kategori baru ini:",
        parse_mode="Markdown",
        reply_markup=get_transaction_type_keyboard(prefix="cat:new_type"),
    )
    await callback.answer()


@router.callback_query(
    CategoryState.waiting_for_type_selection, F.data.startswith("cat:new_type:")
)
async def handle_add_cat_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Save category type and prompt for category name."""
    tx_type = callback.data.split(":")[2]
    await state.update_data(cat_type=tx_type)
    await state.set_state(CategoryState.waiting_for_category_name)

    type_label = "Pemasukan" if tx_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    await callback.message.edit_text(
        f"➕ *Kategori {type_label}*\n\n"
        "Silakan ketik *nama kategori baru* (contoh: 'Investasi' atau 'Uang Kos'):\n\n"
        "_(Ketik melalui pesan chat atau /cancel untuk batal)_",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(CategoryState.waiting_for_category_name)
async def handle_add_cat_name(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Validate and persist new custom category."""
    name = (message.text or "").strip()
    user = await UserService.get_by_telegram_id(session, message.from_user.id)
    data = await state.get_data()
    cat_type = data.get("cat_type", TransactionType.PENGELUARAN.value)

    cat, err = await CategoryService.create_category(
        session=session,
        user_id=user.id,
        name=name,
        transaction_type=cat_type,
    )

    if err:
        await message.answer(
            f"⚠️ Gagal membuat kategori: {err}\n\nSilakan ketik nama lain:"
        )
        return

    await state.clear()
    type_label = "Pemasukan" if cat_type == TransactionType.PEMASUKAN.value else "Pengeluaran"
    await message.answer(
        f"✅ *Kategori Berhasil Dibuat!*\n\n"
        f"🏷️ Nama: *{cat.name}*\n"
        f"📌 Tipe: {type_label}\n\n"
        "Kategori ini kini langsung tersedia saat mencatat transaksi.",
        parse_mode="Markdown",
        reply_markup=get_categories_menu_keyboard(),
    )


# --- Rename Category Flow ---
@router.callback_query(F.data.startswith("cat:rename:"))
async def start_rename_category(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Prompt user for new category name."""
    cat_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    cat = await CategoryService.get_by_id(session, user.id, cat_id)

    if not cat:
        await callback.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    await state.set_state(CategoryState.waiting_for_rename_input)
    await state.update_data(cat_id=cat.id, old_name=cat.name)

    await callback.message.edit_text(
        f"✏️ *UBAH NAMA KATEGORI*\n\n"
        f"Nama saat ini: *{cat.name}*\n\n"
        "Ketikkan nama baru untuk kategori ini melalui chat:",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(CategoryState.waiting_for_rename_input)
async def handle_rename_cat_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Apply new name to category."""
    new_name = (message.text or "").strip()
    data = await state.get_data()
    cat_id = data.get("cat_id")
    user = await UserService.get_by_telegram_id(session, message.from_user.id)

    cat, err = await CategoryService.rename_category(
        session=session,
        user_id=user.id,
        category_id=cat_id,
        new_name=new_name,
    )

    if err:
        await message.answer(
            f"⚠️ Gagal mengubah nama: {err}\n\nSilakan ketik nama lain:"
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Nama kategori berhasil diperbarui menjadi: *{cat.name}*",
        parse_mode="Markdown",
        reply_markup=get_categories_menu_keyboard(),
    )


# --- Delete Category Flow ---
@router.callback_query(F.data.startswith("cat:delete:"))
async def handle_delete_category(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Delete category after verifying no transactions reference it."""
    cat_id = int(callback.data.split(":")[2])
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)

    success, msg = await CategoryService.delete_category(
        session=session,
        user_id=user.id,
        category_id=cat_id,
    )

    if not success:
        # Show alert or message explaining references exist
        await callback.message.edit_text(
            f"⚠️ *Tidak Dapat Menghapus Kategori*\n\n{msg}",
            parse_mode="Markdown",
            reply_markup=get_categories_menu_keyboard(),
        )
        await callback.answer("Gagal menghapus kategori.", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ {msg}",
        parse_mode="Markdown",
        reply_markup=get_categories_menu_keyboard(),
    )
    await callback.answer("Kategori berhasil dihapus!")

