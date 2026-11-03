"""Category service for managing built-in and custom categories."""

import logging
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.db.models import Category, Transaction

logger = logging.getLogger(__name__)


class CategoryService:
    @staticmethod
    async def get_categories(
        session: AsyncSession,
        user_id: int,
        transaction_type: str | None = None,
    ) -> list[Category]:
        """Fetch categories belonging to user_id, optionally filtered by transaction type."""
        stmt = select(Category).where(Category.user_id == user_id)
        if transaction_type:
            stmt = stmt.where(Category.transaction_type == transaction_type)
        stmt = stmt.order_by(Category.is_default.desc(), Category.name.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int, category_id: int) -> Category | None:
        """Fetch a specific category ensuring it belongs to user_id."""
        stmt = select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_category(
        session: AsyncSession,
        user_id: int,
        name: str,
        transaction_type: str,
    ) -> tuple[Category | None, str]:
        """Create a custom category for the user.
        
        Returns:
            tuple[Category | None, str]: (category, error_message_or_empty)
        """
        clean_name = name.strip()
        if not clean_name:
            return None, "Nama kategori tidak boleh kosong."

        if len(clean_name) > 50:
            return None, "Nama kategori maksimal 50 karakter."

        if transaction_type not in (TransactionType.PEMASUKAN.value, TransactionType.PENGELUARAN.value):
            return None, "Tipe transaksi tidak valid."

        # Check for duplicate
        stmt = select(Category).where(
            Category.user_id == user_id,
            Category.transaction_type == transaction_type,
            func.lower(Category.name) == clean_name.lower(),
        )
        existing = await session.execute(stmt)
        if existing.scalar_one_or_none():
            return None, f"Kategori '{clean_name}' sudah ada untuk {transaction_type.lower()}."

        category = Category(
            user_id=user_id,
            name=clean_name,
            transaction_type=transaction_type,
            is_default=False,
        )
        session.add(category)
        await session.flush()
        logger.info("User %d created custom category '%s' (%s)", user_id, clean_name, transaction_type)
        return category, ""

    @staticmethod
    async def rename_category(
        session: AsyncSession,
        user_id: int,
        category_id: int,
        new_name: str,
    ) -> tuple[Category | None, str]:
        """Rename an existing category belonging to the user."""
        clean_name = new_name.strip()
        if not clean_name:
            return None, "Nama kategori tidak boleh kosong."

        if len(clean_name) > 50:
            return None, "Nama kategori maksimal 50 karakter."

        category = await CategoryService.get_by_id(session, user_id, category_id)
        if not category:
            return None, "Kategori tidak ditemukan."

        # Check duplicate
        stmt = select(Category).where(
            Category.user_id == user_id,
            Category.transaction_type == category.transaction_type,
            func.lower(Category.name) == clean_name.lower(),
            Category.id != category_id,
        )
        existing = await session.execute(stmt)
        if existing.scalar_one_or_none():
            return None, f"Kategori '{clean_name}' sudah ada."

        category.name = clean_name
        await session.flush()
        logger.info("User %d renamed category %d to '%s'", user_id, category_id, clean_name)
        return category, ""

    @staticmethod
    async def delete_category(
        session: AsyncSession,
        user_id: int,
        category_id: int,
    ) -> tuple[bool, str]:
        """Delete a category if it belongs to user and is not referenced by any transactions."""
        category = await CategoryService.get_by_id(session, user_id, category_id)
        if not category:
            return False, "Kategori tidak ditemukan."

        # Check if transactions reference this category
        stmt = select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
        )
        tx_count_res = await session.execute(stmt)
        tx_count = tx_count_res.scalar() or 0

        if tx_count > 0:
            return (
                False,
                f"Kategori '{category.name}' tidak dapat dihapus karena masih digunakan oleh {tx_count} transaksi. "
                "Silakan ubah atau hapus transaksi terkait terlebih dahulu.",
            )

        await session.delete(category)
        await session.flush()
        logger.info("User %d deleted category %d ('%s')", user_id, category_id, category.name)
        return True, f"Kategori '{category.name}' berhasil dihapus."

