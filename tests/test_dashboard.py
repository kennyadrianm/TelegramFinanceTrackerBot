"""Tests for dashboard calculations, initial balance, and live updates."""

from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.db.models import User
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_dashboard_initial_balance_is_zero(
    async_session: AsyncSession, user_a: User
):
    """Test 12a: Initial user balance is strictly Rp0."""
    summary = await TransactionService.get_financial_summary(async_session, user_a.id)
    assert summary["current_balance"] == 0
    assert summary["total_income"] == 0
    assert summary["total_expense"] == 0
    assert len(summary["recent_transactions"]) == 0


@pytest.mark.asyncio
async def test_dashboard_calculations_and_updates(
    async_session: AsyncSession, user_a: User
):
    """Test 12b: Balance = Total Income - Total Expense, reflecting CRUD updates."""
    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    exp_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PENGELUARAN.value
    )

    # 1. Add Income Rp1.500.000
    tx_inc, _ = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=1500000,
        transaction_date=date(2026, 11, 1),
    )

    # 2. Add Expense Rp500.000
    tx_exp, _ = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=exp_cats[0].id,
        transaction_type=TransactionType.PENGELUARAN.value,
        amount=500000,
        transaction_date=date(2026, 11, 2),
    )

    summary = await TransactionService.get_financial_summary(async_session, user_a.id)
    assert summary["total_income"] == 1500000
    assert summary["total_expense"] == 500000
    assert summary["current_balance"] == 1000000
    assert len(summary["recent_transactions"]) == 2

    # 3. Update expense from 500.000 to 700.000
    await TransactionService.update_transaction(
        session=async_session,
        user_id=user_a.id,
        transaction_id=tx_exp.id,
        amount=700000,
    )
    summary_after_edit = await TransactionService.get_financial_summary(
        async_session, user_a.id
    )
    assert summary_after_edit["total_expense"] == 700000
    assert summary_after_edit["current_balance"] == 800000

    # 4. Delete income
    await TransactionService.delete_transaction(
        session=async_session, user_id=user_a.id, transaction_id=tx_inc.id
    )
    summary_after_del = await TransactionService.get_financial_summary(
        async_session, user_a.id
    )
    assert summary_after_del["total_income"] == 0
    assert summary_after_del["total_expense"] == 700000
    assert summary_after_del["current_balance"] == -700000

