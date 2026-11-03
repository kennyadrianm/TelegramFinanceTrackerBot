"""Automatic financial report scheduler with duplicate prevention and safe restart handling."""

import asyncio
from datetime import date
import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.constants import ReportType
from app.core.timezone import (
    JAKARTA_TZ,
    get_month_range,
    get_week_range,
    is_last_day_of_month,
    now_wib,
    today_wib,
)
from app.db.models import ReportPreference, User
from app.db.session import get_db_session
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=JAKARTA_TZ)


async def check_and_send_scheduled_reports(bot: Bot) -> None:
    """Tick executed every minute in Asia/Jakarta to evaluate and dispatch scheduled reports."""
    current_dt = now_wib()
    current_time_str = current_dt.strftime("%H:%M")
    current_date = current_dt.date()
    current_weekday = current_dt.weekday()  # 0=Monday, 6=Sunday
    is_last_day = is_last_day_of_month(current_date)

    logger.debug(
        "Evaluating scheduled reports at %s (weekday=%d, is_last_day=%s)",
        current_time_str,
        current_weekday,
        is_last_day,
    )

    try:
        async with get_db_session() as session:
            # Query all users with report preferences
            stmt = select(ReportPreference).options(selectinload(ReportPreference.user))
            result = await session.execute(stmt)
            preferences = result.scalars().all()

            for pref in preferences:
                user = pref.user
                if not user:
                    continue

                # 1. Daily Report Check
                if pref.daily_enabled and pref.daily_time == current_time_str:
                    await _process_report_for_user(
                        bot=bot,
                        session=session,
                        user=user,
                        report_type=ReportType.DAILY,
                        period_start=current_date,
                        period_end=current_date,
                    )

                # 2. Weekly Report Check (e.g. Sunday)
                if (
                    pref.weekly_enabled
                    and pref.weekly_day == current_weekday
                    and pref.weekly_time == current_time_str
                ):
                    mon, sun = get_week_range(current_date)
                    await _process_report_for_user(
                        bot=bot,
                        session=session,
                        user=user,
                        report_type=ReportType.WEEKLY,
                        period_start=mon,
                        period_end=sun,
                    )

                # 3. Monthly Report Check (e.g. Last day of month)
                if (
                    pref.monthly_enabled
                    and is_last_day
                    and pref.monthly_time == current_time_str
                ):
                    first_d, last_d = get_month_range(current_date)
                    await _process_report_for_user(
                        bot=bot,
                        session=session,
                        user=user,
                        report_type=ReportType.MONTHLY,
                        period_start=first_d,
                        period_end=last_d,
                    )

    except Exception as e:
        logger.error("Error evaluating scheduled reports: %s", e, exc_info=True)


async def _process_report_for_user(
    bot: Bot,
    session,
    user: User,
    report_type: ReportType,
    period_start: date,
    period_end: date,
) -> None:
    """Send scheduled report if not already delivered for this user and period."""
    already_delivered = await ReportService.is_report_already_delivered(
        session=session,
        user_id=user.id,
        report_type=report_type.value,
        period_start=period_start,
        period_end=period_end,
    )
    if already_delivered:
        logger.debug(
            "Report %s for user %d (%s to %s) was already delivered. Skipping.",
            report_type.value,
            user.id,
            period_start,
            period_end,
        )
        return

    try:
        report_data = await ReportService.get_report_data(
            session=session,
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
        )
        message_text = ReportService.format_report_message(
            report_type=report_type,
            data=report_data,
            is_automatic=True,
        )

        await bot.send_message(
            chat_id=user.telegram_user_id,
            text=message_text,
            parse_mode="Markdown",
        )

        # Record delivery to prevent any future duplicates for this period
        await ReportService.record_delivery(
            session=session,
            user_id=user.id,
            report_type=report_type.value,
            period_start=period_start,
            period_end=period_end,
        )
        logger.info(
            "Successfully sent automatic %s report to user %d (tg_id=%d)",
            report_type.value,
            user.id,
            user.telegram_user_id,
        )
    except Exception as err:
        logger.error(
            "Failed sending scheduled report to telegram_id %d: %s",
            user.telegram_user_id,
            err,
        )


def start_scheduler(bot: Bot) -> None:
    """Start background scheduler checking reports every minute."""
    if not scheduler.running:
        scheduler.add_job(
            check_and_send_scheduled_reports,
            "cron",
            minute="*",
            second="0",
            args=[bot],
            id="scheduled_financial_reports",
            replace_existing=True,
            misfire_grace_time=30,
        )
        scheduler.start()
        logger.info("Scheduler started with Asia/Jakarta timezone.")


def stop_scheduler() -> None:
    """Gracefully stop background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")

