"""Tests for transaction exports to CSV and Excel, and data isolation."""

import csv
from datetime import date
from openpyxl import load_workbook
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ExportFormat, ExportPeriod, TransactionType
from app.db.models import User
from app.services.category_service import CategoryService
from app.services.export_service import ExportService
from app.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_export_csv(async_session: AsyncSession, user_a: User):
    """Test 17: CSV generation with correct headers and data rows."""
    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=500000,
        transaction_date=date(2026, 11, 1),
        note="Proyek Web",
    )

    file_path, count = await ExportService.export_transactions(
        session=async_session,
        user_id=user_a.id,
        export_format=ExportFormat.CSV,
        period=ExportPeriod.ALL,
    )
    assert count == 1
    assert file_path is not None
    assert file_path.exists()

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = list(csv.reader(f))
            assert len(reader) == 2  # header + 1 row
            headers = reader[0]
            assert "Nominal (Rp)" in headers
            assert "Tipe Transaksi" in headers
            row = reader[1]
            assert row[2] == "Pemasukan"
            assert row[4] == "500000"
            assert row[5] == "Proyek Web"
    finally:
        ExportService.cleanup_file(file_path)
        assert not file_path.exists()


@pytest.mark.asyncio
async def test_export_excel(async_session: AsyncSession, user_a: User):
    """Test 18: Excel (.xlsx) generation with proper openpyxl sheets and summary rows."""
    exp_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PENGELUARAN.value
    )
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=exp_cats[0].id,
        transaction_type=TransactionType.PENGELUARAN.value,
        amount=75000,
        transaction_date=date(2026, 11, 2),
        note="Bensin",
    )

    file_path, count = await ExportService.export_transactions(
        session=async_session,
        user_id=user_a.id,
        export_format=ExportFormat.EXCEL,
        period=ExportPeriod.ALL,
    )
    assert count == 1
    assert file_path is not None
    assert file_path.exists()

    try:
        wb = load_workbook(file_path)
        ws = wb.active
        assert ws.title == "Laporan Transaksi"
        assert ws.cell(row=1, column=1).value == "No"
        assert ws.cell(row=2, column=3).value == "Pengeluaran"
        assert ws.cell(row=2, column=5).value == 75000
        assert ws.cell(row=2, column=6).value == "Bensin"
    finally:
        ExportService.cleanup_file(file_path)
        assert not file_path.exists()


@pytest.mark.asyncio
async def test_export_ownership_isolation(
    async_session: AsyncSession, user_a: User, user_b: User
):
    """Test 19: Export ownership isolation between users."""
    cats_a = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    cats_b = await CategoryService.get_categories(
        async_session, user_b.id, TransactionType.PEMASUKAN.value
    )

    # User A transaction
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cats_a[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=1000000,
        note="Secret A",
    )
    # User B transaction
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_b.id,
        category_id=cats_b[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=2000000,
        note="Secret B",
    )

    # Export for User A
    file_a, count_a = await ExportService.export_transactions(
        session=async_session,
        user_id=user_a.id,
        export_format=ExportFormat.CSV,
        period=ExportPeriod.ALL,
    )
    assert count_a == 1

    try:
        with open(file_a, "r", encoding="utf-8-sig") as f:
            content = f.read()
            assert "Secret A" in content
            assert "Secret B" not in content
    finally:
        ExportService.cleanup_file(file_a)

