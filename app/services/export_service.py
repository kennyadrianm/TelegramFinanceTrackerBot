"""Transaction export service generating CSV and Excel files."""

import csv
from datetime import date
import logging
from pathlib import Path
import tempfile
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.constants import ExportFormat, ExportPeriod, TransactionType, format_idr
from app.core.timezone import (
    JAKARTA_TZ,
    format_date_id,
    get_month_range,
    get_week_range,
    today_wib,
)
from app.db.models import Transaction

logger = logging.getLogger(__name__)


class ExportService:
    @staticmethod
    def resolve_date_range(
        period: ExportPeriod,
        custom_start: date | None = None,
        custom_end: date | None = None,
    ) -> tuple[date | None, date | None]:
        """Resolve date boundaries for a given export period."""
        today = today_wib()
        if period == ExportPeriod.TODAY:
            return today, today
        elif period == ExportPeriod.THIS_WEEK:
            return get_week_range(today)
        elif period == ExportPeriod.THIS_MONTH:
            return get_month_range(today)
        elif period == ExportPeriod.CUSTOM:
            return custom_start, custom_end
        return None, None

    @staticmethod
    async def get_user_transactions_for_export(
        session: AsyncSession,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Fetch transactions strictly belonging to user_id for the given period."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .options(selectinload(Transaction.category))
        )
        if start_date:
            stmt = stmt.where(Transaction.transaction_date >= start_date)
        if end_date:
            stmt = stmt.where(Transaction.transaction_date <= end_date)

        stmt = stmt.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def generate_csv(
        cls,
        session: AsyncSession,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[Path | None, int]:
        """Generate a CSV file of user transactions."""
        txs = await cls.get_user_transactions_for_export(
            session, user_id, start_date, end_date
        )
        if not txs:
            return None, 0

        settings.ensure_directories()
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            prefix=f"transaksi_user_{user_id}_",
            dir=settings.EXPORTS_DIR,
            delete=False,
            newline="",
            encoding="utf-8-sig",  # UTF-8 with BOM for Excel compatibility
        )
        file_path = Path(temp_file.name)

        writer = csv.writer(temp_file)
        writer.writerow(
            [
                "No",
                "Tanggal",
                "Tipe Transaksi",
                "Kategori",
                "Nominal (Rp)",
                "Catatan",
                "Waktu Dibuat (WIB)",
            ]
        )

        for idx, tx in enumerate(txs, start=1):
            cat_name = tx.category.name if tx.category else "-"
            type_label = (
                "Pemasukan"
                if tx.transaction_type == TransactionType.PEMASUKAN.value
                else "Pengeluaran"
            )
            created_str = (
                tx.created_at.astimezone(JAKARTA_TZ).strftime("%d-%m-%Y %H:%M:%S")
                if tx.created_at
                else "-"
            )
            writer.writerow(
                [
                    idx,
                    format_date_id(tx.transaction_date),
                    type_label,
                    cat_name,
                    tx.amount,
                    tx.note or "-",
                    created_str,
                ]
            )

        temp_file.close()
        return file_path, len(txs)

    @classmethod
    async def generate_excel(
        cls,
        session: AsyncSession,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[Path | None, int]:
        """Generate a styled Excel (.xlsx) file of user transactions."""
        txs = await cls.get_user_transactions_for_export(
            session, user_id, start_date, end_date
        )
        if not txs:
            return None, 0

        settings.ensure_directories()
        wb = Workbook()
        ws = wb.active
        ws.title = "Laporan Transaksi"

        # Headers
        headers = [
            "No",
            "Tanggal",
            "Tipe Transaksi",
            "Kategori",
            "Nominal (Rp)",
            "Catatan",
            "Waktu Dibuat (WIB)",
        ]
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="1F497D", end_color="1F497D", fill_type="solid"
        )
        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        )

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        total_income = 0
        total_expense = 0

        for idx, tx in enumerate(txs, start=1):
            cat_name = tx.category.name if tx.category else "-"
            is_inc = tx.transaction_type == TransactionType.PEMASUKAN.value
            type_label = "Pemasukan" if is_inc else "Pengeluaran"
            if is_inc:
                total_income += tx.amount
            else:
                total_expense += tx.amount

            created_str = (
                tx.created_at.astimezone(JAKARTA_TZ).strftime("%d-%m-%Y %H:%M:%S")
                if tx.created_at
                else "-"
            )

            row = [
                idx,
                format_date_id(tx.transaction_date),
                type_label,
                cat_name,
                tx.amount,
                tx.note or "-",
                created_str,
            ]
            ws.append(row)
            row_idx = idx + 1

            # Cell formatting
            ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=2).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=3).alignment = Alignment(horizontal="center")
            ws.cell(row=row_idx, column=5).number_format = '#,##0'

            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).border = thin_border

        # Summary rows at bottom
        last_row = len(txs) + 2
        ws.cell(row=last_row, column=4, value="Total Pemasukan").font = Font(bold=True)
        cell_inc = ws.cell(row=last_row, column=5, value=total_income)
        cell_inc.font = Font(bold=True, color="008000")
        cell_inc.number_format = '#,##0'

        ws.cell(row=last_row + 1, column=4, value="Total Pengeluaran").font = Font(bold=True)
        cell_exp = ws.cell(row=last_row + 1, column=5, value=total_expense)
        cell_exp.font = Font(bold=True, color="CC0000")
        cell_exp.number_format = '#,##0'

        ws.cell(row=last_row + 2, column=4, value="Saldo Bersih (Net)").font = Font(bold=True)
        cell_net = ws.cell(row=last_row + 2, column=5, value=total_income - total_expense)
        cell_net.font = Font(bold=True)
        cell_net.number_format = '#,##0'

        # Auto-fit column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".xlsx",
            prefix=f"transaksi_user_{user_id}_",
            dir=settings.EXPORTS_DIR,
            delete=False,
        )
        file_path = Path(temp_file.name)
        temp_file.close()

        wb.save(file_path)
        return file_path, len(txs)

    @classmethod
    async def export_transactions(
        cls,
        session: AsyncSession,
        user_id: int,
        export_format: ExportFormat,
        period: ExportPeriod,
        custom_start: date | None = None,
        custom_end: date | None = None,
    ) -> tuple[Path | None, int]:
        """Unified exporter routing to CSV or Excel."""
        start_date, end_date = cls.resolve_date_range(period, custom_start, custom_end)
        if export_format == ExportFormat.CSV:
            return await cls.generate_csv(session, user_id, start_date, end_date)
        return await cls.generate_excel(session, user_id, start_date, end_date)

    @staticmethod
    def cleanup_file(path: Path | None) -> None:
        """Safely delete exported temporary file."""
        if path and path.exists():
            try:
                path.unlink()
                logger.debug("Cleaned up temporary export file: %s", path)
            except Exception as e:
                logger.warning("Failed to clean up file %s: %s", path, e)

