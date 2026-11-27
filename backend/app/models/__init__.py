"""Import every model here so Base.metadata knows about all tables (Alembic needs this)."""
from app.models.user import User
from app.models.group import Group, GroupInvite, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.settlement import Settlement

__all__ = ["User", "Group", "GroupMember", "GroupInvite", "Expense", "ExpenseSplit", "Settlement"]
