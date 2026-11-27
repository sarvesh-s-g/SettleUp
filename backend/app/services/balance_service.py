"""Balance calculation.

    net balance = total paid - total share owed + settlements paid - settlements received

Positive -> the member should RECEIVE money. Negative -> the member OWES money.
Balances are always recomputed from the stored expenses, splits and settlements;
there is no stored "balance" column that could drift out of sync.
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Expense, ExpenseSplit, GroupMember, Settlement, User


@dataclass
class BalanceRow:
    user_id: int
    name: str
    is_member: bool
    total_paid_paise: int = 0
    total_share_paise: int = 0
    settlements_paid_paise: int = 0
    settlements_received_paise: int = 0

    @property
    def net_balance_paise(self) -> int:
        return (
            self.total_paid_paise
            - self.total_share_paise
            + self.settlements_paid_paise
            - self.settlements_received_paise
        )


def _sum_by_user(db: Session, statement) -> dict[int, int]:
    """Run a 'SELECT user_id, SUM(...) ... GROUP BY user_id' and return a dict."""
    return {user_id: int(total) for user_id, total in db.execute(statement).all()}


def get_user_total_share(db: Session, group_id: int, user_id: int) -> int:
    """Return the user's assigned shares for all expenses in one group."""
    total = db.scalar(
        select(func.coalesce(func.sum(ExpenseSplit.share_amount_paise), 0))
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(Expense.group_id == group_id, ExpenseSplit.user_id == user_id)
    )
    return int(total)


def compute_group_balances(db: Session, group_id: int) -> list[BalanceRow]:
    """Return one BalanceRow per current member (plus any former member who still
    appears in the group's records), sorted by name."""
    # 1. Total each user PAID for expenses in this group.
    paid = _sum_by_user(
        db,
        select(Expense.paid_by, func.sum(Expense.amount_paise))
        .where(Expense.group_id == group_id)
        .group_by(Expense.paid_by),
    )
    # 2. Total each user OWES (their shares) - needs a JOIN to know the group.
    owed = _sum_by_user(
        db,
        select(ExpenseSplit.user_id, func.sum(ExpenseSplit.share_amount_paise))
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(Expense.group_id == group_id)
        .group_by(ExpenseSplit.user_id),
    )
    # 3. Repayments each user has MADE.
    settled_out = _sum_by_user(
        db,
        select(Settlement.paid_by, func.sum(Settlement.amount_paise))
        .where(Settlement.group_id == group_id)
        .group_by(Settlement.paid_by),
    )
    # 4. Repayments each user has RECEIVED.
    settled_in = _sum_by_user(
        db,
        select(Settlement.paid_to, func.sum(Settlement.amount_paise))
        .where(Settlement.group_id == group_id)
        .group_by(Settlement.paid_to),
    )

    member_ids = set(
        db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id)).all()
    )
    all_ids = member_ids | paid.keys() | owed.keys() | settled_out.keys() | settled_in.keys()
    if not all_ids:
        return []

    names = dict(db.execute(select(User.id, User.name).where(User.id.in_(all_ids))).all())

    rows = [
        BalanceRow(
            user_id=user_id,
            name=names[user_id],
            is_member=user_id in member_ids,
            total_paid_paise=paid.get(user_id, 0),
            total_share_paise=owed.get(user_id, 0),
            settlements_paid_paise=settled_out.get(user_id, 0),
            settlements_received_paise=settled_in.get(user_id, 0),
        )
        for user_id in all_ids
    ]
    rows.sort(key=lambda row: (row.name.lower(), row.user_id))
    return rows


def get_net_balances(db: Session, group_id: int) -> dict[int, int]:
    """Convenience wrapper: {user_id: net_balance_paise}."""
    return {row.user_id: row.net_balance_paise for row in compute_group_balances(db, group_id)}


def get_user_net_balance(db: Session, group_id: int, user_id: int) -> int:
    return get_net_balances(db, group_id).get(user_id, 0)
