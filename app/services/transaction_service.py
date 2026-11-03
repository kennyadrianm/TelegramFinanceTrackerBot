"""Transaction service handling CRUD operations, calculations, and data isolation."""

from datetime import date
import logging
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import TransactionType
from app.core.timezone import today_wib
from app.db.models import Category, Transaction
from app.services.category_service import CategoryService

logger = logging.getLogger(__name__)


class TransactionService:
    @staticmethod
    async def create_transaction(
        session: AsyncSession,
        user_id: int,
        category_id: int,
        transaction_type: str,
        amount: int,
        transaction_date: date | None = None,
        note: str | None = None,
    ) -> tuple[Transaction | None, str]:
        """Create a new transaction with strict validation and user isolation.
        
        Returns:
            tuple[Transaction | None, str]: (transaction, error_message)
        """
        if amount <= 0:
            return None, "Nominal transaksi harus berupa bilangan bulat positif lebih besar dari Rp0."

        if transaction_type not in (TransactionType.PEMASUKAN.value, TransactionType.PENGELUARAN.value):
            return None, "Tipe transaksi tidak valid."

        # Validate category belongs to user and matches transaction_type
        category = await CategoryService.get_by_id(session, user_id, category_id)
        if not category:
            return None, "Kategori tidak ditemukan atau bukan milik Anda."

        if category.transaction_type != transaction_type:
            return None, f"Kategori '{category.name}' tidak sesuai dengan tipe transaksi {transaction_type}."

        tx_date = transaction_date or today_wib()
        clean_note = note.strip() if note and note.strip() else None
        if clean_note and len(clean_note) > 500:
            return None, "Catatan transaksi maksimal 500 karakter."

        tx = Transaction(
            user_id=user_id,
            category_id=category_id,
            transaction_type=transaction_type,
            amount=amount,
            transaction_date=tx_date,
            note=clean_note,
        )
        session.add(tx)
        await session.flush()
        # Eager load category for downstream display
        await session.refresh(tx, ["category"])
        logger.info(
            "Created tx %d for user %d: type=%s, amount=%d, date=%s",
            tx.id,
            user_id,
            transaction_type,
            amount,
            tx_date,
        )
        return tx, ""

    @staticmethod
    async def get_by_id(
        session: AsyncSession, user_id: int, transaction_id: int
    ) -> Transaction | None:
        """Fetch a single transaction verifying user ownership."""
        stmt = (
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
            .options(selectinload(Transaction.category))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_transaction(
        session: AsyncSession,
        user_id: int,
        transaction_id: int,
        category_id: int | None = None,
        transaction_type: str | None = None,
        amount: int | None = None,
        transaction_date: date | None = None,
        note: str | None = None,
        clear_note: bool = False,
    ) -> tuple[Transaction | None, str]:
        """Update transaction fields with ownership and category compatibility checks."""
        tx = await TransactionService.get_by_id(session, user_id, transaction_id)
        if not tx:
            return None, "Transaksi tidak ditemukan."

        target_type = transaction_type or tx.transaction_type
        target_cat_id = category_id if category_id is not None else tx.category_id

        if amount is not None:
            if amount <= 0:
                return None, "Nominal transaksi harus lebih besar dari Rp0."
            tx.amount = amount

        # Category compatibility check
        category = await CategoryService.get_by_id(session, user_id, target_cat_id)
        if not category:
            return None, "Kategori tidak ditemukan atau bukan milik Anda."

        if category.transaction_type != target_type:
            return (
                None,
                f"Kategori '{category.name}' tidak cocok dengan tipe transaksi {target_type}.",
            )

        tx.transaction_type = target_type
        tx.category_id = target_cat_id

        if transaction_date is not None:
            tx.transaction_date = transaction_date

        if clear_note:
            tx.note = None
        elif note is not None:
            clean_note = note.strip()
            if len(clean_note) > 500:
                return None, "Catatan transaksi maksimal 500 karakter."
            tx.note = clean_note if clean_note else None

        await session.flush()
        await session.refresh(tx, ["category"])
        logger.info("Updated tx %d for user %d", tx.id, user_id)
        return tx, ""

    @staticmethod
    async def delete_transaction(
        session: AsyncSession, user_id: int, transaction_id: int
    ) -> tuple[bool, str]:
        """Hard delete a transaction after verifying ownership."""
        tx = await TransactionService.get_by_id(session, user_id, transaction_id)
        if not tx:
            return False, "Transaksi tidak ditemukan."

        await session.delete(tx)
        await session.flush()
        logger.info("Deleted tx %d for user %d", transaction_id, user_id)
        return True, "Transaksi berhasil dihapus."

    @staticmethod
    async def get_transactions(
        session: AsyncSession,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Get filtered and paginated transactions for a user, sorted newest first."""
        base_stmt = select(Transaction).where(Transaction.user_id == user_id)

        if transaction_type:
            base_stmt = base_stmt.where(Transaction.transaction_type == transaction_type)
        if category_id:
            base_stmt = base_stmt.where(Transaction.category_id == category_id)
        if start_date:
            base_stmt = base_stmt.where(Transaction.transaction_date >= start_date)
        if end_date:
            base_stmt = base_stmt.where(Transaction.transaction_date <= end_date)

        # Count total matching
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count = (await session.execute(count_stmt)).scalar() or 0

        # Fetch page items
        query = (
            base_stmt.options(selectinload(Transaction.category))
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(query)
        items = list(result.scalars().all())

        return items, total_count

    @staticmethod
    async def get_financial_summary(session: AsyncSession, user_id: int) -> dict:
        """Calculate total income, total expense, current balance, and fetch recent transactions."""
        # Total income
        income_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.PEMASUKAN.value,
        )
        total_income = (await session.execute(income_stmt)).scalar() or 0

        # Total expense
        expense_stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.PENGELUARAN.value,
        )
        total_expense = (await session.execute(expense_stmt)).scalar() or 0

        # Balance = Income - Expense (Rp0 initial)
        current_balance = total_income - total_expense

        # Recent 5 transactions
        recent_stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .options(selectinload(Transaction.category))
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(5)
        )
        recent_txs = list((await session.execute(recent_stmt)).scalars().all())

        return {
            "total_income": int(total_income),
            "total_expense": int(total_expense),
            "current_balance": int(current_balance),
            "recent_transactions": recent_txs,
        }

