"""Tests for user registration, duplicate handling, and default category initialization."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_CATEGORIES,
    TransactionType,
)
from app.services.category_service import CategoryService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_new_user_registration(async_session: AsyncSession):
    """Test 1: New user registration automatically creates user record."""
    user, is_created = await UserService.get_or_create_user(
        session=async_session,
        telegram_user_id=99988877,
        username="john_doe",
        first_name="John",
    )
    assert is_created is True
    assert user.id is not None
    assert user.telegram_user_id == 99988877
    assert user.username == "john_doe"
    assert user.first_name == "John"


@pytest.mark.asyncio
async def test_duplicate_registration(async_session: AsyncSession):
    """Test 2: Duplicate registration returns existing user without duplicating."""
    user1, is_created1 = await UserService.get_or_create_user(
        session=async_session,
        telegram_user_id=12345678,
        username="original_user",
        first_name="Original",
    )
    assert is_created1 is True

    # Second registration with updated username
    user2, is_created2 = await UserService.get_or_create_user(
        session=async_session,
        telegram_user_id=12345678,
        username="updated_user",
        first_name="Updated",
    )
    assert is_created2 is False
    assert user2.id == user1.id
    assert user2.username == "updated_user"
    assert user2.first_name == "Updated"


@pytest.mark.asyncio
async def test_default_category_initialization(async_session: AsyncSession):
    """Test 3: Default income and expense categories are properly seeded on registration."""
    user, _ = await UserService.get_or_create_user(
        session=async_session,
        telegram_user_id=33344455,
        username="cat_test",
        first_name="CatTester",
    )

    income_cats = await CategoryService.get_categories(
        session=async_session,
        user_id=user.id,
        transaction_type=TransactionType.PEMASUKAN.value,
    )
    expense_cats = await CategoryService.get_categories(
        session=async_session,
        user_id=user.id,
        transaction_type=TransactionType.PENGELUARAN.value,
    )

    income_names = {c.name for c in income_cats}
    expense_names = {c.name for c in expense_cats}

    for expected_inc in DEFAULT_INCOME_CATEGORIES:
        assert expected_inc in income_names

    for expected_exp in DEFAULT_EXPENSE_CATEGORIES:
        assert expected_exp in expense_names

    # Check is_default flag
    assert all(c.is_default for c in income_cats)
    assert all(c.is_default for c in expense_cats)

