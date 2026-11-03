"""Financial report calculation, formatting, and delivery tracking service."""

from datetime import date
import logging
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ReportType, TransactionType, format_idr
from app.core.timezone import (
    format_date_id,
    format_date_long_id,
    get_month_range,
    get_week_range,
    now_wib,
    today_wib,
)
from app.db.models import Category, ReportDelivery, ReportPreference, Transaction

logger = logging.getLogger(__name__)


class ReportService:
    @staticmethod
    async def get_report_data(
        session: AsyncSession,
        user_id: int,
        period_start: date,
        period_end: date,
    ) -> dict:
        """Calculate report statistics for the given date range (inclusive)."""
        # Income total
        stmt_inc = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.PEMASUKAN.value,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        total_income = int((await session.execute(stmt_inc)).scalar() or 0)

        # Expense total
        stmt_exp = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.PENGELUARAN.value,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        total_expense = int((await session.execute(stmt_exp)).scalar() or 0)

        # Total transaction count
        stmt_count = select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        tx_count = int((await session.execute(stmt_count)).scalar() or 0)

        # Income breakdown by category
        stmt_inc_cat = (
            select(Category.name, func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.PEMASUKAN.value,
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        inc_breakdown_raw = (await session.execute(stmt_inc_cat)).all()
        income_breakdown = []
        for cat_name, amt in inc_breakdown_raw:
            pct = (amt / total_income * 100) if total_income > 0 else 0.0
            income_breakdown.append({"category": cat_name, "amount": int(amt), "percentage": pct})

        # Expense breakdown by category
        stmt_exp_cat = (
            select(Category.name, func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.PENGELUARAN.value,
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        exp_breakdown_raw = (await session.execute(stmt_exp_cat)).all()
        expense_breakdown = []
        for cat_name, amt in exp_breakdown_raw:
            pct = (amt / total_expense * 100) if total_expense > 0 else 0.0
            expense_breakdown.append({"category": cat_name, "amount": int(amt), "percentage": pct})

        net_balance = total_income - total_expense

        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": net_balance,
            "transaction_count": tx_count,
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown,
        }

    @staticmethod
    def format_report_message(report_type: ReportType, data: dict, is_automatic: bool = False) -> str:
        """Format report data into a beautiful Indonesian Telegram Markdown text."""
        start = data["period_start"]
        end = data["period_end"]

        if report_type == ReportType.DAILY:
            period_str = format_date_long_id(start)
            title = f"📊 *LAPORAN KEUANGAN HARIAN{' (OTOMATIS)' if is_automatic else ''}*"
        elif report_type == ReportType.WEEKLY:
            period_str = f"{format_date_id(start)} s/d {format_date_id(end)}"
            title = f"📊 *LAPORAN KEUANGAN MINGGUAN{' (OTOMATIS)' if is_automatic else ''}*"
        else:
            period_str = f"{format_date_long_id(start)} s/d {format_date_long_id(end)}"
            title = f"📊 *LAPORAN KEUANGAN BULANAN{' (OTOMATIS)' if is_automatic else ''}*"

        lines = [
            title,
            f"🗓 *Periode:* {period_str}",
            f"🔢 *Jumlah Transaksi:* {data['transaction_count']}",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🟢 *Total Pemasukan:* `{format_idr(data['total_income'])}`",
            f"🔴 *Total Pengeluaran:* `{format_idr(data['total_expense'])}`",
            f"⚖️ *Arus Kas Bersih (Net):* `{format_idr(data['net_balance'])}`",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # Breakdown Pemasukan
        lines.append("🟢 *Rincian Pemasukan per Kategori:*")
        if data["income_breakdown"]:
            for item in data["income_breakdown"]:
                lines.append(
                    f" • {item['category']}: `{format_idr(item['amount'])}` ({item['percentage']:.1f}%)"
                )
        else:
            lines.append(" • _(Tidak ada pemasukan)_")
        lines.append("")

        # Breakdown Pengeluaran
        lines.append("🔴 *Rincian Pengeluaran per Kategori:*")
        if data["expense_breakdown"]:
            for item in data["expense_breakdown"]:
                lines.append(
                    f" • {item['category']}: `{format_idr(item['amount'])}` ({item['percentage']:.1f}%)"
                )
        else:
            lines.append(" • _(Tidak ada pengeluaran)_")

        return "\n".join(lines)

    @staticmethod
    async def is_report_already_delivered(
        session: AsyncSession,
        user_id: int,
        report_type: str,
        period_start: date,
        period_end: date,
    ) -> bool:
        """Check if a report has already been delivered for this period to prevent duplicates."""
        stmt = select(ReportDelivery).where(
            ReportDelivery.user_id == user_id,
            ReportDelivery.report_type == report_type,
            ReportDelivery.period_start == period_start,
            ReportDelivery.period_end == period_end,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def record_delivery(
        session: AsyncSession,
        user_id: int,
        report_type: str,
        period_start: date,
        period_end: date,
    ) -> ReportDelivery:
        """Record report delivery in the database."""
        delivery = ReportDelivery(
            user_id=user_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            sent_at=now_wib(),
        )
        session.add(delivery)
        await session.flush()
        return delivery

    @staticmethod
    async def get_or_create_preference(
        session: AsyncSession, user_id: int
    ) -> ReportPreference:
        """Retrieve user's report scheduling preferences, creating defaults if absent."""
        stmt = select(ReportPreference).where(ReportPreference.user_id == user_id)
        result = await session.execute(stmt)
        pref = result.scalar_one_or_none()
        if not pref:
            pref = ReportPreference(
                user_id=user_id,
                daily_enabled=False,
                daily_time="21:00",
                weekly_enabled=False,
                weekly_day=6,
                weekly_time="21:00",
                monthly_enabled=False,
                monthly_time="21:00",
            )
            session.add(pref)
            await session.flush()
        return pref

