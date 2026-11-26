from datetime import date, datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CATEGORIES = (
    "food", "groceries", "rent", "utilities", "transport",
    "entertainment", "shopping", "other",
)
SPLIT_EQUAL = "equal"
SPLIT_CUSTOM = "custom"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_expenses_amount_positive"),
        CheckConstraint("split_type IN ('equal', 'custom')", name="ck_expenses_split_type"),
        CheckConstraint(
            "category IN ('food', 'groceries', 'rent', 'utilities', 'transport', "
            "'entertainment', 'shopping', 'other')",
            name="ck_expenses_category",
        ),
        # Expense history is always "expenses of one group, filtered/sorted by date".
        Index("ix_expenses_group_id_expense_date", "group_id", "expense_date"),
        Index("ix_expenses_paid_by", "paid_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    paid_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    # Money is stored as whole paise (Rs 125.50 -> 12550). Never as a float.
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    split_type: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    group: Mapped["Group"] = relationship(back_populates="expenses")
    payer: Mapped["User"] = relationship()
    # Deleting an expense deletes its splits (ORM cascade + ON DELETE CASCADE in the DB).
    splits: Mapped[list["ExpenseSplit"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", passive_deletes=True,
        order_by="ExpenseSplit.user_id",
    )


class ExpenseSplit(Base):
    """One row per participant of an expense: who owes how much of it."""

    __tablename__ = "expense_splits"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_splits_expense_user"),
        CheckConstraint("share_amount_paise > 0", name="ck_expense_splits_share_positive"),
        Index("ix_expense_splits_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    share_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    expense: Mapped["Expense"] = relationship(back_populates="splits")
    user: Mapped["User"] = relationship()
