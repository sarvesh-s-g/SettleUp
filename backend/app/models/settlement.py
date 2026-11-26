from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Settlement(Base):
    """A repayment made outside the app (cash/UPI), recorded so balances update."""

    __tablename__ = "settlements"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_settlements_amount_positive"),
        CheckConstraint("paid_by <> paid_to", name="ck_settlements_different_users"),
        Index("ix_settlements_group_id_settled_at", "group_id", "settled_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    paid_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    paid_to: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    settled_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    group: Mapped["Group"] = relationship(back_populates="settlements")
    payer: Mapped["User"] = relationship(foreign_keys=[paid_by])
    receiver: Mapped["User"] = relationship(foreign_keys=[paid_to])
