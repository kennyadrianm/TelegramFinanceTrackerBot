"""Data export handlers: exporting transactions to CSV or Excel with temp file cleanup."""

from datetime import date
import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_EXPORT, ExportFormat, ExportPeriod
from app.core.timezone import parse_date_str
from app.keyboards.inline_keyboards import (
    get_export_format_keyboard,
    get_export_period_keyboard,
)
from app.services.export_service import ExportService
from app.services.user_service import UserService
from app.states.form_states import ExportState

logger = logging.getLogger(__name__)
router = Router(name="export_router")


@router.message(F.text == BTN_EXPORT)
@router.message(Command("ekspor"))
async def start_export_flow(message: Message, state: FSMContext) -> None:
    """Initiate export: prompt user to select export format."""
    await state.clear()
    await state.set_state(ExportState.waiting_for_format)
    await message.answer(
        "📁 *EKSPOR DATA TRANSAKSI*\n\n"
        "Silakan pilih format file ekspor yang Anda inginkan:",
        parse_mode="Markdown",
        reply_markup=get_export_format_keyboard(),
    )


@router.callback_query(
    ExportState.waiting_for_format, F.data.startswith("export:fmt:")
)
async def handle_format_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Save format and ask for export period."""
    fmt = callback.data.split(":")[2]
    await state.update_data(format=fmt)
    await state.set_state(ExportState.waiting_for_period)

    fmt_label = "CSV (.csv)" if fmt == ExportFormat.CSV.value else "Excel (.xlsx)"
    await callback.message.edit_text(
        f"📄 *Format Dipilih:* *{fmt_label}*\n\n"
        "Silakan tentukan *periode transaksi* yang ingin diekspor:",
        parse_mode="Markdown",
        reply_markup=get_export_period_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    ExportState.waiting_for_period, F.data.startswith("export:prd:")
)
async def handle_period_selected(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Handle standard period selection or prompt for custom date range."""
    prd_code = callback.data.split(":")[2]
    data = await state.get_data()
    fmt = ExportFormat(data["format"])

    if prd_code == ExportPeriod.CUSTOM.value:
        await state.update_data(period=prd_code)
        await state.set_state(ExportState.waiting_for_custom_start)
        await callback.message.edit_text(
            "🔍 *Rentang Tanggal Kustom*\n\n"
            "Silakan masukkan *tanggal awal* dalam format `DD-MM-YYYY` (contoh: `01-10-2026`):",
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    # Standard period: execute export immediately
    period = ExportPeriod(prd_code)
    await _execute_export_and_send(
        callback.message, session, callback.from_user.id, fmt, period
    )
    await state.clear()
    await callback.answer()


@router.message(ExportState.waiting_for_custom_start)
async def handle_custom_start(message: Message, state: FSMContext) -> None:
    """Receive custom start date."""
    parsed = parse_date_str(message.text or "")
    if not parsed:
        await message.answer(
            "⚠️ Format tanggal awal tidak valid. Gunakan format `DD-MM-YYYY` (contoh: `01-10-2026`):"
        )
        return

    await state.update_data(custom_start=parsed.isoformat())
    await state.set_state(ExportState.waiting_for_custom_end)
    await message.answer(
        "Silakan masukkan *tanggal akhir* dalam format `DD-MM-YYYY` (contoh: `31-10-2026`):",
        parse_mode="Markdown",
    )


@router.message(ExportState.waiting_for_custom_end)
async def handle_custom_end(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Receive custom end date, validate range, and execute export."""
    parsed = parse_date_str(message.text or "")
    if not parsed:
        await message.answer(
            "⚠️ Format tanggal akhir tidak valid. Gunakan format `DD-MM-YYYY` (contoh: `31-10-2026`):"
        )
        return

    data = await state.get_data()
    start_date = date.fromisoformat(data["custom_start"])

    if parsed < start_date:
        await message.answer(
            "⚠️ Tanggal akhir tidak boleh mendahului tanggal awal. Silakan ketik tanggal akhir yang valid:"
        )
        return

    fmt = ExportFormat(data["format"])
    await _execute_export_and_send(
        message,
        session,
        message.from_user.id,
        fmt,
        ExportPeriod.CUSTOM,
        start_date=start_date,
        end_date=parsed,
    )
    await state.clear()


async def _execute_export_and_send(
    message_or_target: Message,
    session: AsyncSession,
    telegram_user_id: int,
    fmt: ExportFormat,
    period: ExportPeriod,
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """Generate the export document, send it to the user, and delete temp file."""
    user = await UserService.get_by_telegram_id(session, telegram_user_id)
    if not user:
        await message_or_target.answer("Pengguna tidak ditemukan.")
        return

    wait_msg = await message_or_target.answer("⏳ Menyiapkan file ekspor data Anda...")

    file_path, count = await ExportService.export_transactions(
        session=session,
        user_id=user.id,
        export_format=fmt,
        period=period,
        custom_start=start_date,
        custom_end=end_date,
    )

    try:
        if count == 0 or file_path is None:
            await wait_msg.edit_text(
                "ℹ️ Tidak ada transaksi yang tercatat pada periode yang Anda pilih.\n"
                "File ekspor tidak dapat dibuat karena tidak ada data."
            )
            return

        doc = FSInputFile(
            path=str(file_path),
            filename=f"laporan_transaksi_{user.id}_{fmt.value.lower()}.{'csv' if fmt == ExportFormat.CSV else 'xlsx'}",
        )

        caption = (
            f"✅ *Ekspor Berhasil!*\n\n"
            f"📄 Format: *{fmt.value}*\n"
            f"🗓 Periode: *{period.label}*\n"
            f"🔢 Total Data: *{count} transaksi*"
        )

        await message_or_target.answer_document(
            document=doc,
            caption=caption,
            parse_mode="Markdown",
        )
        await wait_msg.delete()
    finally:
        # Guarantee cleanup of temporary export files
        ExportService.cleanup_file(file_path)

