"""Pytest configuration and test database fixtures."""

from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.models import User
from app.services.user_service import UserService


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a pristine in-memory SQLite database engine for each test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session for testing."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def user_a(async_session: AsyncSession) -> User:
    """Fixture providing a pre-registered test user A."""
    user, _ = await UserService.get_or_create_user(
        session=async_session,
        telegram_user_id=11111111,
        username="user_alpha",
        first_name="Budi",
    )
    await async_session.commit()
    return user


@pytest_asyncio.fixture(scope="function")
async def user_b(async_session: AsyncSession) -> User:
    """Fixture providing a second isolated test user B."""
    user, _ = await UserService.get_or_create_user(
        session=async_session,
        telegram_user_id=22222222,
        username="user_beta",
        first_name="Siti",
    )
    await async_session.commit()
    return user

