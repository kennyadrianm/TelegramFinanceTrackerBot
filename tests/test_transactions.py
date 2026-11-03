"""Tests for transaction CRUD, validation, editing, and ownership isolation."""

from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.db.models import User
from app.handlers.transaction_add import parse_rupiah_input
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_income_creation(async_session: AsyncSession, user_a: User):
    """Test 6: Income transaction creation."""
    income_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    cat = income_cats[0]

    tx, err = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=5000000,
        transaction_date=date(2026, 11, 2),
        note="Gaji Bulan Ini",
    )
    assert err == ""
    assert tx is not None
    assert tx.id is not None
    assert tx.amount == 5000000
    assert tx.transaction_type == TransactionType.PEMASUKAN.value
    assert tx.note == "Gaji Bulan Ini"
    assert tx.user_id == user_a.id


@pytest.mark.asyncio
async def test_expense_creation(async_session: AsyncSession, user_a: User):
    """Test 7: Expense transaction creation."""
    expense_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PENGELUARAN.value
    )
    cat = expense_cats[0]

    tx, err = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
        transaction_type=TransactionType.PENGELUARAN.value,
        amount=45000,
        transaction_date=date(2026, 11, 3),
        note="Makan siang",
    )
    assert err == ""
    assert tx is not None
    assert tx.amount == 45000
    assert tx.transaction_type == TransactionType.PENGELUARAN.value


@pytest.mark.asyncio
async def test_transaction_amount_validation(async_session: AsyncSession, user_a: User):
    """Test 8: Transaction amount validation (positive integers only, no floats)."""
    income_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    cat = income_cats[0]

    # Negative amount
    tx_neg, err_neg = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=-10000,
    )
    assert tx_neg is None
    assert "positif" in err_neg

    # Zero amount
    tx_zero, err_zero = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=0,
    )
    assert tx_zero is None
    assert "positif" in err_zero

    # Parser validation
    assert parse_rupiah_input("50000") == 50000
    assert parse_rupiah_input("50.000") == 50000
    assert parse_rupiah_input("Rp 50.000") == 50000
    assert parse_rupiah_input("rp 1.500.000") == 1500000
    assert parse_rupiah_input("0") is None
    assert parse_rupiah_input("-50000") is None
    assert parse_rupiah_input("abc") is None
    assert parse_rupiah_input("50,50") is None  # Fractional float cents rejected


@pytest.mark.asyncio
async def test_transaction_editing(async_session: AsyncSession, user_a: User):
    """Test 9: Transaction editing with category compatibility validation."""
    inc_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    exp_cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PENGELUARAN.value
    )

    # Initial: Income
    tx, _ = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=inc_cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=100000,
        transaction_date=date(2026, 11, 1),
    )

    # Edit amount & note
    tx_updated, err = await TransactionService.update_transaction(
        session=async_session,
        user_id=user_a.id,
        transaction_id=tx.id,
        amount=150000,
        note="Updated note",
    )
    assert err == ""
    assert tx_updated.amount == 150000
    assert tx_updated.note == "Updated note"

    # Incompatible edit: changing type to PENGELUARAN while keeping inc_cats[0]
    tx_bad, err_bad = await TransactionService.update_transaction(
        session=async_session,
        user_id=user_a.id,
        transaction_id=tx.id,
        transaction_type=TransactionType.PENGELUARAN.value,
        category_id=inc_cats[0].id,
    )
    assert tx_bad is None
    assert "tidak cocok" in err_bad

    # Compatible type and category change
    tx_good, err_good = await TransactionService.update_transaction(
        session=async_session,
        user_id=user_a.id,
        transaction_id=tx.id,
        transaction_type=TransactionType.PENGELUARAN.value,
        category_id=exp_cats[0].id,
    )
    assert err_good == ""
    assert tx_good.transaction_type == TransactionType.PENGELUARAN.value
    assert tx_good.category_id == exp_cats[0].id


@pytest.mark.asyncio
async def test_transaction_deletion_logic(async_session: AsyncSession, user_a: User):
    """Test 10: Permanent transaction deletion."""
    cats = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    tx, _ = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cats[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=250000,
    )

    # Deletion
    del_ok, msg = await TransactionService.delete_transaction(
        session=async_session, user_id=user_a.id, transaction_id=tx.id
    )
    assert del_ok is True
    assert "berhasil dihapus" in msg

    # Verification: record must no longer exist (hard deleted)
    fetched = await TransactionService.get_by_id(
        session=async_session, user_id=user_a.id, transaction_id=tx.id
    )
    assert fetched is None


@pytest.mark.asyncio
async def test_transaction_ownership_validation(
    async_session: AsyncSession, user_a: User, user_b: User
):
    """Test 11: Transaction ownership validation between independent users."""
    cats_a = await CategoryService.get_categories(
        async_session, user_a.id, TransactionType.PEMASUKAN.value
    )
    tx_a, _ = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cats_a[0].id,
        transaction_type=TransactionType.PEMASUKAN.value,
        amount=750000,
    )

    # User B tries to view User A's transaction
    view_attempt = await TransactionService.get_by_id(
        session=async_session, user_id=user_b.id, transaction_id=tx_a.id
    )
    assert view_attempt is None

    # User B tries to edit User A's transaction
    edit_attempt, edit_err = await TransactionService.update_transaction(
        session=async_session,
        user_id=user_b.id,
        transaction_id=tx_a.id,
        amount=999999,
    )
    assert edit_attempt is None
    assert "tidak ditemukan" in edit_err

    # User B tries to delete User A's transaction
    del_attempt, del_err = await TransactionService.delete_transaction(
        session=async_session, user_id=user_b.id, transaction_id=tx_a.id
    )
    assert del_attempt is False
    assert "tidak ditemukan" in del_err

