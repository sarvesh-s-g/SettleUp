from datetime import date

from pydantic import BaseModel


class RecentExpense(BaseModel):
    id: int
    group_id: int
    group_name: str
    description: str
    amount_paise: int
    category: str
    paid_by_name: str
    expense_date: date
    my_share_paise: int


class CategoryTotal(BaseModel):
    category: str
    my_share_paise: int


class MonthlyGroupShare(BaseModel):
    group_id: int
    group_name: str
    my_share_paise: int


class MonthlyTotal(BaseModel):
    month: str  # "YYYY-MM"
    my_share_paise: int
    group_shares: list[MonthlyGroupShare]


class GroupBalance(BaseModel):
    group_id: int
    group_name: str
    net_balance_paise: int


class DashboardSuggestion(BaseModel):
    group_id: int
    group_name: str
    from_user_id: int
    from_name: str
    to_user_id: int
    to_name: str
    amount_paise: int


class DashboardResponse(BaseModel):
    group_count: int
    my_total_paid_paise: int
    my_total_share_paise: int
    my_net_balance_paise: int
    group_balances: list[GroupBalance]
    recent_expenses: list[RecentExpense]
    category_breakdown: list[CategoryTotal]
    monthly_summary: list[MonthlyTotal]
    suggested_settlements: list[DashboardSuggestion]
