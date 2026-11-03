"""User management service."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES, TransactionType
from app.db.models import Category, ReportPreference, User

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_user_id: int) -> User | None:
        """Find a user by Telegram User ID."""
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_or_create_user(
        cls,
        session: AsyncSession,
        telegram_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> tuple[User, bool]:
        """Retrieve existing user or register a new user with default categories and report preferences.
        
        Returns:
            tuple[User, bool]: (user, is_created)
        """
        user = await cls.get_by_telegram_id(session, telegram_user_id)
        if user:
            # Update profile if changed
            updated = False
            if user.username != username:
                user.username = username
                updated = True
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if updated:
                await session.flush()
            return user, False

        # Create new user
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
        )
        session.add(user)
        await session.flush()  # assign user.id

        # Initialize default income categories
        for cat_name in DEFAULT_INCOME_CATEGORIES:
            cat = Category(
                user_id=user.id,
                name=cat_name,
                transaction_type=TransactionType.PEMASUKAN.value,
                is_default=True,
            )
            session.add(cat)

        # Initialize default expense categories
        for cat_name in DEFAULT_EXPENSE_CATEGORIES:
            cat = Category(
                user_id=user.id,
                name=cat_name,
                transaction_type=TransactionType.PENGELUARAN.value,
                is_default=True,
            )
            session.add(cat)

        # Initialize default report preferences
        preference = ReportPreference(
            user_id=user.id,
            daily_enabled=False,
            daily_time="21:00",
            weekly_enabled=False,
            weekly_day=6,  # Sunday
            weekly_time="21:00",
            monthly_enabled=False,
            monthly_time="21:00",
        )
        session.add(preference)

        await session.flush()
        logger.info("Registered new user with telegram_id=%d, user_id=%d", telegram_user_id, user.id)
        return user, True

