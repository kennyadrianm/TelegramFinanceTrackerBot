"""Inline keyboards for interactive conversation flows."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.constants import ExportFormat, ExportPeriod, ReportType, TransactionType
from app.db.models import Category, ReportPreference


def get_transaction_type_keyboard(prefix: str = "tx:type") -> InlineKeyboardMarkup:
    """Keyboard to select Income or Expense."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Pemasukan", callback_data=f"{prefix}:{TransactionType.PEMASUKAN.value}"
                ),
                InlineKeyboardButton(
                    text="🔴 Pengeluaran", callback_data=f"{prefix}:{TransactionType.PENGELUARAN.value}"
                ),
            ],
            [InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")],
        ]
    )


def get_category_picker_keyboard(
    categories: list[Category], prefix: str = "tx:cat"
) -> InlineKeyboardMarkup:
    """Generate inline buttons for available categories in 2 columns."""
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []

    for cat in categories:
        btn = InlineKeyboardButton(
            text=f"🏷️ {cat.name}", callback_data=f"{prefix}:{cat.id}"
        )
        current_row.append(btn)
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append([InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_date_option_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting transaction date."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Gunakan Hari Ini (WIB)", callback_data="tx:date:today")],
            [InlineKeyboardButton(text="🗓️ Buka Kalender Interaktif", callback_data="tx:date:calendar")],
            [InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")],
        ]
    )


def get_skip_note_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to skip optional note."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Lewati Catatan", callback_data="tx:note:skip")],
            [InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")],
        ]
    )


def get_transaction_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard for saving transaction."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💾 Simpan", callback_data="tx:confirm:save"),
                InlineKeyboardButton(text="✏️ Perbaiki", callback_data="tx:confirm:fix"),
            ],
            [InlineKeyboardButton(text="❌ Batalkan", callback_data="tx:confirm:cancel")],
        ]
    )


def get_fix_field_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to select which field to fix/edit in a transaction."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Tipe", callback_data="tx:fix:type"),
                InlineKeyboardButton(text="💰 Nominal", callback_data="tx:fix:amount"),
            ],
            [
                InlineKeyboardButton(text="🏷️ Kategori", callback_data="tx:fix:category"),
                InlineKeyboardButton(text="📅 Tanggal", callback_data="tx:fix:date"),
            ],
            [
                InlineKeyboardButton(text="📝 Catatan", callback_data="tx:fix:note"),
            ],
            [InlineKeyboardButton(text="🔙 Kembali ke Konfirmasi", callback_data="tx:fix:back")],
        ]
    )


def get_delete_confirmation_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """Explicit confirmation keyboard for permanent deletion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Ya, Hapus", callback_data=f"tx:del_confirm:{transaction_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Batal", callback_data=f"tx:del_cancel:{transaction_id}"
                ),
            ]
        ]
    )


def get_transaction_detail_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """Action buttons on a transaction detail view."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Ubah", callback_data=f"tx:edit_init:{transaction_id}"),
                InlineKeyboardButton(text="🗑️ Hapus", callback_data=f"tx:del_prompt:{transaction_id}"),
            ],
            [InlineKeyboardButton(text="🔙 Kembali ke Riwayat", callback_data="history:back")],
        ]
    )


def get_history_navigation_keyboard(
    page: int, total_pages: int, tx_ids: list[tuple[int, str]]
) -> InlineKeyboardMarkup:
    """Pagination and transaction item picker for history."""
    rows: list[list[InlineKeyboardButton]] = []

    # Transaction items in the current page
    for tx_id, label in tx_ids:
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"tx:view:{tx_id}")
        ])

    # Navigation buttons
    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="◀️ Sebelumnya", callback_data=f"history:page:{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"📄 {page}/{max(total_pages, 1)}", callback_data="action:ignore")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="▶️ Selanjutnya", callback_data=f"history:page:{page + 1}")
        )
    rows.append(nav_row)

    # Filter row
    rows.append([
        InlineKeyboardButton(text="🔍 Filter Riwayat", callback_data="history:filters"),
        InlineKeyboardButton(text="🔄 Segarkan", callback_data=f"history:page:{page}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_history_filter_keyboard(
    active_type: str | None, active_period: str | None
) -> InlineKeyboardMarkup:
    """Filter options for history."""
    type_label = "Semua"
    if active_type == TransactionType.PEMASUKAN.value:
        type_label = "🟢 Pemasukan"
    elif active_type == TransactionType.PENGELUARAN.value:
        type_label = "🔴 Pengeluaran"

    period_label = {
        "ALL": "Semua Waktu",
        "TODAY": "Hari Ini",
        "THIS_WEEK": "Minggu Ini",
        "THIS_MONTH": "Bulan Ini",
    }.get(active_period or "ALL", "Semua Waktu")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Tipe: {type_label}", callback_data="hist_fil:toggle_type"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Periode: {period_label}", callback_data="hist_fil:toggle_period"
                )
            ],
            [
                InlineKeyboardButton(text="✅ Terapkan Filter", callback_data="history:page:1"),
                InlineKeyboardButton(text="🔄 Reset Filter", callback_data="hist_fil:reset"),
            ],
        ]
    )


def get_categories_menu_keyboard() -> InlineKeyboardMarkup:
    """Menu to choose between viewing Income or Expense categories, or adding a new one."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Kategori Pemasukan", callback_data="cat:list:PEMASUKAN"
                ),
                InlineKeyboardButton(
                    text="🔴 Kategori Pengeluaran", callback_data="cat:list:PENGELUARAN"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➕ Buat Kategori Baru", callback_data="cat:add:start"
                )
            ],
        ]
    )


def get_category_item_keyboard(
    category_id: int, is_default: bool
) -> InlineKeyboardMarkup:
    """Actions on a specific category."""
    rows = [
        [InlineKeyboardButton(text="✏️ Ubah Nama", callback_data=f"cat:rename:{category_id}")],
        [InlineKeyboardButton(text="🗑️ Hapus Kategori", callback_data=f"cat:delete:{category_id}")],
        [InlineKeyboardButton(text="🔙 Kembali", callback_data="cat:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_report_menu_keyboard() -> InlineKeyboardMarkup:
    """Menu for choosing manual financial report periods."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Laporan Hari Ini", callback_data="report:daily")],
            [InlineKeyboardButton(text="📅 Laporan Minggu Ini (Senin-Minggu)", callback_data="report:weekly")],
            [InlineKeyboardButton(text="🗓️ Laporan Bulan Ini", callback_data="report:monthly")],
        ]
    )


def get_export_format_keyboard() -> InlineKeyboardMarkup:
    """Format selection for export."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 File CSV (.csv)", callback_data="export:fmt:CSV"),
                InlineKeyboardButton(text="📊 File Excel (.xlsx)", callback_data="export:fmt:EXCEL"),
            ],
            [InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")],
        ]
    )


def get_export_period_keyboard() -> InlineKeyboardMarkup:
    """Period selection for export."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Hari Ini", callback_data="export:prd:TODAY"),
                InlineKeyboardButton(text="🗓️ Minggu Ini", callback_data="export:prd:THIS_WEEK"),
            ],
            [
                InlineKeyboardButton(text="📆 Bulan Ini", callback_data="export:prd:THIS_MONTH"),
                InlineKeyboardButton(text="📁 Semua Riwayat", callback_data="export:prd:ALL"),
            ],
            [
                InlineKeyboardButton(text="🔍 Rentang Kustom (DD-MM-YYYY)", callback_data="export:prd:CUSTOM")
            ],
            [InlineKeyboardButton(text="❌ Batalkan", callback_data="action:cancel")],
        ]
    )


def get_settings_keyboard(pref: ReportPreference) -> InlineKeyboardMarkup:
    """Settings menu for configuring automatic reports."""
    daily_status = "🟢 AKTIF" if pref.daily_enabled else "⚪ NONAKTIF"
    weekly_status = "🟢 AKTIF" if pref.weekly_enabled else "⚪ NONAKTIF"
    monthly_status = "🟢 AKTIF" if pref.monthly_enabled else "⚪ NONAKTIF"

    days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    weekly_day_str = days_id[pref.weekly_day] if 0 <= pref.weekly_day <= 6 else "Minggu"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Laporan Harian: {daily_status} ({pref.daily_time})",
                    callback_data="set:toggle:daily",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏱ Atur Jam Harian", callback_data="set:time:daily"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Laporan Mingguan: {weekly_status} ({weekly_day_str} {pref.weekly_time})",
                    callback_data="set:toggle:weekly",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📅 Atur Hari & Jam Mingguan", callback_data="set:time:weekly"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Laporan Bulanan: {monthly_status} ({pref.monthly_time})",
                    callback_data="set:toggle:monthly",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏱ Atur Jam Bulanan", callback_data="set:time:monthly"
                )
            ],
        ]
    )

