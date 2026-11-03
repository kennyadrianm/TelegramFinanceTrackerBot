"""Financial reports handler for on-demand manual report generation."""

import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BTN_REPORT, ReportType
from app.core.timezone import get_month_range, get_week_range, today_wib
from app.keyboards.inline_keyboards import get_report_menu_keyboard
from app.services.report_service import ReportService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="report_router")


@router.message(F.text == BTN_REPORT)
@router.message(Command("laporan"))
async def show_report_menu(
    message: Message, state: FSMContext
) -> None:
    """Show options for generating manual financial reports."""
    await state.clear()
    await message.answer(
        "📈 *LAPORAN KEUANGAN*\n\n"
        "Pilih periode laporan keuangan yang ingin Anda tampilkan:",
        parse_mode="Markdown",
        reply_markup=get_report_menu_keyboard(),
    )


@router.callback_query(F.data == "report:daily")
async def generate_daily_report(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Generate daily report for today in Asia/Jakarta."""
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    today = today_wib()

    data = await ReportService.get_report_data(
        session=session,
        user_id=user.id,
        period_start=today,
        period_end=today,
    )
    text = ReportService.format_report_message(ReportType.DAILY, data)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_report_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report:weekly")
async def generate_weekly_report(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Generate weekly report for Monday to Sunday of the current week."""
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    today = today_wib()
    mon, sun = get_week_range(today)

    data = await ReportService.get_report_data(
        session=session,
        user_id=user.id,
        period_start=mon,
        period_end=sun,
    )
    text = ReportService.format_report_message(ReportType.WEEKLY, data)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_report_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report:monthly")
async def generate_monthly_report(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Generate monthly report for the current calendar month."""
    user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    today = today_wib()
    first_d, last_d = get_month_range(today)

    data = await ReportService.get_report_data(
        session=session,
        user_id=user.id,
        period_start=first_d,
        period_end=last_d,
    )
    text = ReportService.format_report_message(ReportType.MONTHLY, data)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_report_menu_keyboard(),
    )
    await callback.answer()

