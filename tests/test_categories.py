"""Tests for category management, custom creation, ownership isolation, and deletion checks."""

from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.db.models import User
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_custom_category_creation(async_session: AsyncSession, user_a: User):
    """Test 4: Creating a custom category."""
    cat, err = await CategoryService.create_category(
        session=async_session,
        user_id=user_a.id,
        name="Crypto Dividen",
        transaction_type=TransactionType.PEMASUKAN.value,
    )
    assert err == ""
    assert cat is not None
    assert cat.name == "Crypto Dividen"
    assert cat.is_default is False
    assert cat.user_id == user_a.id


@pytest.mark.asyncio
async def test_custom_category_ownership(
    async_session: AsyncSession, user_a: User, user_b: User
):
    """Test 5: Category ownership isolation between multiple users."""
    # User A creates a custom category
    cat_a, _ = await CategoryService.create_category(
        session=async_session,
        user_id=user_a.id,
        name="Side Project A",
        transaction_type=TransactionType.PEMASUKAN.value,
    )

    # User B should NOT be able to view it by ID
    cat_lookup = await CategoryService.get_by_id(
        session=async_session, user_id=user_b.id, category_id=cat_a.id
    )
    assert cat_lookup is None

    # User B cannot rename User A's category
    renamed, err = await CategoryService.rename_category(
        session=async_session,
        user_id=user_b.id,
        category_id=cat_a.id,
        new_name="Hacked Name",
    )
    assert renamed is None
    assert "tidak ditemukan" in err

    # User B cannot delete User A's category
    del_ok, del_err = await CategoryService.delete_category(
        session=async_session,
        user_id=user_b.id,
        category_id=cat_a.id,
    )
    assert del_ok is False
    assert "tidak ditemukan" in del_err


@pytest.mark.asyncio
async def test_delete_category_with_referenced_transactions(
    async_session: AsyncSession, user_a: User
):
    """Requirement B: Cannot delete a category referenced by existing transactions."""
    cat, _ = await CategoryService.create_category(
        session=async_session,
        user_id=user_a.id,
        name="Gym Membership",
        transaction_type=TransactionType.PENGELUARAN.value,
    )

    # Create a transaction referencing this category
    tx, err = await TransactionService.create_transaction(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
        transaction_type=TransactionType.PENGELUARAN.value,
        amount=350000,
        transaction_date=date(2026, 11, 1),
    )
    assert err == ""
    assert tx is not None

    # Attempt to delete category -> MUST fail
    deleted, msg = await CategoryService.delete_category(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
    )
    assert deleted is False
    assert "masih digunakan oleh 1 transaksi" in msg

    # Delete transaction first
    del_tx_ok, _ = await TransactionService.delete_transaction(
        session=async_session, user_id=user_a.id, transaction_id=tx.id
    )
    assert del_tx_ok is True

    # Now deleting category should succeed
    deleted_now, msg_now = await CategoryService.delete_category(
        session=async_session,
        user_id=user_a.id,
        category_id=cat.id,
    )
    assert deleted_now is True
    assert "berhasil dihapus" in msg_now

