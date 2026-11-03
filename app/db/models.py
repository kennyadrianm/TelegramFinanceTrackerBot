"""SQLAlchemy models for the finance tracker."""

from datetime import date, datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timezone import now_wib
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, nullable=False
    )

    # Relationships
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    report_preference: Mapped["ReportPreference | None"] = relationship(
        "ReportPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    report_deliveries: Mapped[list["ReportDelivery"]] = relationship(
        "ReportDelivery", back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "transaction_type", "name", name="uq_user_type_cat_name"),
        Index("ix_categories_user_type", "user_id", "transaction_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_tx_user_date", "user_id", "transaction_date"),
        Index("ix_tx_user_type", "user_id", "transaction_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, onupdate=now_wib, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    category: Mapped["Category"] = relationship("Category", back_populates="transactions")


class ReportPreference(Base):
    __tablename__ = "report_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    daily_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_time: Mapped[str] = mapped_column(String(5), default="21:00", nullable=False)
    weekly_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weekly_day: Mapped[int] = mapped_column(Integer, default=6, nullable=False)  # 0=Monday, 6=Sunday
    weekly_time: Mapped[str] = mapped_column(String(5), default="21:00", nullable=False)
    monthly_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    monthly_time: Mapped[str] = mapped_column(String(5), default="21:00", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, onupdate=now_wib, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="report_preference")


class ReportDelivery(Base):
    __tablename__ = "report_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "report_type", "period_start", "period_end", name="uq_report_delivery"
        ),
        Index("ix_delivery_user_type_period", "user_id", "report_type", "period_start", "period_end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_wib, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="report_deliveries")

