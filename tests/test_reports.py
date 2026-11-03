"""Tests for financial report calculations, date boundaries, preferences, and duplicate prevention."""

from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ReportType, TransactionType
from app.core.timezone import get_month_range, get_week_range
from app.db.models import User
from app.services.category_service import CategoryService
from app.services.report_service import ReportService
from app.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_daily_report_calculations(async_session: AsyncSession, user_a: User):
    """Test 13: Daily report calculations."""
    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    exp_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PENGELUARAN.value
    )
    target_date = date(2026, 11, 3)

    # Add income & expense on target_date
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=2000000,
        transaction_date=target_date,
    )
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=exp_cats[0].id,
        transaction_type=TransactionType.PENGELUARAN.value,
        amount=150000,
        transaction_date=target_date,
    )

    data = await ReportService.get_report_data(
        session=async_session,
        user_id=user_a.id,
        period_start=target_date,
        period_end=target_date,
    )
    assert data["total_income"] == 2000000
    assert data["total_expense"] == 150000
    assert data["net_balance"] == 1850000
    assert data["transaction_count"] == 2
    assert len(data["income_breakdown"]) == 1
    assert data["income_breakdown"][0]["amount"] == 2000000
    assert data["income_breakdown"][0]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_weekly_report_calculations(async_session: AsyncSession, user_a: User):
    """Test 14: Weekly report calculations following Monday-Sunday."""
    # Suppose week is Monday Nov 2 to Sunday Nov 8, 2026
    sample_day = date(2026, 11, 4)  # Wednesday
    mon, sun = get_week_range(sample_day)
    assert mon == date(2026, 11, 2)
    assert sun == date(2026, 11, 8)

    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )

    # Transaction on Monday
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=500000,
        transaction_date=mon,
    )
    # Transaction on Sunday
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=300000,
        transaction_date=sun,
    )

    data = await ReportService.get_report_data(
        session=async_session,
        user_id=user_a.id,
        period_start=mon,
        period_end=sun,
    )
    assert data["total_income"] == 800000
    assert data["transaction_count"] == 2


@pytest.mark.asyncio
async def test_monthly_report_calculations(async_session: AsyncSession, user_a: User):
    """Test 15: Monthly report calculations following calendar months."""
    first_day, last_day = get_month_range(date(2026, 11, 15))
    assert first_day == date(2026, 11, 1)
    assert last_day == date(2026, 11, 30)

    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    exp_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PENGELUARAN.value
    )

    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=10000000,
        transaction_date=first_day,
    )
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=exp_cats[0].id,
        transaction_type=TransactionType.PENGELUARAN.value,
        amount=2500000,
        transaction_date=last_day,
    )

    data = await ReportService.get_report_data(
        session=async_session,
        user_id=user_a.id,
        period_start=first_day,
        period_end=last_day,
    )
    assert data["total_income"] == 10000000
    assert data["total_expense"] == 2500000
    assert data["net_balance"] == 7500000


@pytest.mark.asyncio
async def test_date_range_boundaries(async_session: AsyncSession, user_a: User):
    """Test 16: Exact boundary inclusiveness and outside date exclusion."""
    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )

    # 1 day before period
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=999,
        transaction_date=date(2026, 10, 31),
    )
    # Start boundary
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=100,
        transaction_date=date(2026, 11, 1),
    )
    # End boundary
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=200,
        transaction_date=date(2026, 11, 5),
    )
    # 1 day after period
    await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=888,
        transaction_date=date(2026, 11, 6),
    )

    data = await ReportService.get_report_data(
        session=async_session,
        user_id=user_a.id,
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 5),
    )
    assert data["total_income"] == 300  # only 100 + 200
    assert data["transaction_count"] == 2


@pytest.mark.asyncio
async def test_report_preference_handling(async_session: AsyncSession, user_a: User):
    """Test 20: Report preferences initialization and customization."""
    pref = await ReportService.get_or_create_preference(async_session, user_a.id)
    assert pref.daily_time == "21:00"
    assert pref.weekly_day == 6
    assert pref.monthly_time == "21:00"

    # Update preferences
    pref.daily_enabled = True
    pref.daily_time = "07:30"
    pref.weekly_enabled = True
    pref.weekly_day = 0  # Monday
    pref.weekly_time = "18:00"
    await async_session.flush()

    reloaded = await ReportService.get_or_create_preference(async_session, user_a.id)
    assert reloaded.daily_enabled is True
    assert reloaded.daily_time == "07:30"
    assert reloaded.weekly_day == 0
    assert reloaded.weekly_time == "18:00"


@pytest.mark.asyncio
async def test_duplicate_report_delivery_prevention(
    async_session: AsyncSession, user_a: User
):
    """Test 21: Duplicate report delivery prevention using ReportDelivery records."""
    target_date = date(2026, 11, 3)

    # Initial check -> not delivered yet
    already = await ReportService.is_report_already_delivered(
        session=async_session,
        user_id=user_a.id,
        report_type=ReportType.DAILY.value,
        period_start=target_date,
        period_end=target_date,
    )
    assert already is False

    # Record delivery
    await ReportService.record_delivery(
        session=async_session,
        user_id=user_a.id,
        report_type=ReportType.DAILY.value,
        period_start=target_date,
        period_end=target_date,
    )

    # Re-check -> must be True!
    already_after = await ReportService.is_report_already_delivered(
        session=async_session,
        user_id=user_a.id,
        report_type=ReportType.DAILY.value,
        period_start=target_date,
        period_end=target_date,
    )
    assert already_after is True

