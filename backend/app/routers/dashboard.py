from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Expense, ExpenseSplit, Group, GroupMember, User
from app.schemas.dashboard import (
    CategoryTotal, DashboardResponse, DashboardSuggestion, GroupBalance, MonthlyTotal, RecentExpense,
)
from app.services.balance_service import compute_group_balances
from app.services.settlement_service import suggest_settlements

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

MONTHS_IN_SUMMARY = 6


def _last_months(today: date, count: int) -> list[str]:
    """['2026-06', ..., '2026-11'] - oldest first, including the current month."""
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def _months_in_range(start: date, end: date) -> list[str]:
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return months


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summary across every group the logged-in user belongs to."""
    today = date.today()
    default_months = _last_months(today, MONTHS_IN_SUMMARY)
    analysis_start = start_date or date.fromisoformat(default_months[0] + "-01")
    analysis_end = end_date or today
    if analysis_start > analysis_end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    me = current_user.id
    my_group_ids = select(GroupMember.group_id).where(GroupMember.user_id == me)
    groups = db.execute(
        select(Group.id, Group.name).where(Group.id.in_(my_group_ids)).order_by(Group.name)
    ).all()

    in_my_groups = Expense.group_id.in_(my_group_ids)
    total_spending = db.scalar(select(func.coalesce(func.sum(Expense.amount_paise), 0)).where(in_my_groups))
    my_paid = db.scalar(
        select(func.coalesce(func.sum(Expense.amount_paise), 0)).where(in_my_groups, Expense.paid_by == me)
    )
    my_share = db.scalar(
        select(func.coalesce(func.sum(ExpenseSplit.share_amount_paise), 0))
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(in_my_groups, ExpenseSplit.user_id == me)
    )

    # Per-group balances and the settlements that involve me.
    group_balances: list[GroupBalance] = []
    suggestions: list[DashboardSuggestion] = []
    for group_id, group_name in groups:
        rows = compute_group_balances(db, group_id)
        names = {r.user_id: r.name for r in rows}
        nets = {r.user_id: r.net_balance_paise for r in rows}
        group_balances.append(
            GroupBalance(group_id=group_id, group_name=group_name, net_balance_paise=nets.get(me, 0))
        )
        for debtor, creditor, amount in suggest_settlements(nets):
            if me in (debtor, creditor):
                suggestions.append(DashboardSuggestion(
                    group_id=group_id, group_name=group_name,
                    from_user_id=debtor, from_name=names[debtor],
                    to_user_id=creditor, to_name=names[creditor], amount_paise=amount,
                ))

    # Recent expenses with my share (LEFT JOIN: I might not be a participant).
    my_split = and_(ExpenseSplit.expense_id == Expense.id, ExpenseSplit.user_id == me)
    recent_rows = db.execute(
        select(Expense, Group.name, User.name, func.coalesce(ExpenseSplit.share_amount_paise, 0))
        .join(Group, Group.id == Expense.group_id)
        .join(User, User.id == Expense.paid_by)
        .outerjoin(ExpenseSplit, my_split)
        .where(in_my_groups)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(8)
    ).all()
    recent = [
        RecentExpense(
            id=e.id, group_id=e.group_id, group_name=group_name, description=e.description,
            amount_paise=e.amount_paise, category=e.category, paid_by_name=payer_name,
            expense_date=e.expense_date, my_share_paise=int(share),
        )
        for e, group_name, payer_name, share in recent_rows
    ]

    category_rows = db.execute(
        select(Expense.category, func.sum(Expense.amount_paise).label("total"))
        .where(in_my_groups, Expense.expense_date >= analysis_start, Expense.expense_date <= analysis_end)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount_paise).desc())
    ).all()

    # Monthly totals are grouped into every calendar month intersecting the selected range.
    months = _months_in_range(analysis_start, analysis_end)
    month_key = func.to_char(Expense.expense_date, "YYYY-MM")
    month_totals = dict(db.execute(
        select(month_key, func.sum(Expense.amount_paise))
        .where(in_my_groups, Expense.expense_date >= analysis_start, Expense.expense_date <= analysis_end)
        .group_by(month_key)
    ).all())
    month_shares = dict(db.execute(
        select(month_key, func.sum(ExpenseSplit.share_amount_paise))
        .join(ExpenseSplit, ExpenseSplit.expense_id == Expense.id)
        .where(
            in_my_groups, ExpenseSplit.user_id == me,
            Expense.expense_date >= analysis_start, Expense.expense_date <= analysis_end,
        )
        .group_by(month_key)
    ).all())

    return DashboardResponse(
        group_count=len(groups),
        total_group_spending_paise=int(total_spending),
        my_total_paid_paise=int(my_paid),
        my_total_share_paise=int(my_share),
        my_net_balance_paise=sum(g.net_balance_paise for g in group_balances),
        group_balances=group_balances,
        recent_expenses=recent,
        category_breakdown=[CategoryTotal(category=c, total_paise=int(t)) for c, t in category_rows],
        monthly_summary=[
            MonthlyTotal(month=m, total_paise=int(month_totals.get(m, 0)), my_share_paise=int(month_shares.get(m, 0)))
            for m in months
        ],
        suggested_settlements=suggestions,
    )
