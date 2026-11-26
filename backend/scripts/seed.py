"""DEVELOPMENT ONLY: fill the database with sample roommates, groups and expenses.

Usage (from the backend folder, after `alembic upgrade head`):
    python -m scripts.seed

All seeded accounts use the password  Password@123
    sarvesh@example.com, rahul@example.com, kiran@example.com, aman@example.com

The script refuses to run twice (it stops if sarvesh@example.com already exists).
"""
from datetime import date, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Expense, ExpenseSplit, Group, GroupMember, Settlement, User
from app.services.balance_service import get_net_balances
from app.services.split_service import split_equally
from app.utils.security import hash_password

PASSWORD = "Password@123"


def days_ago(n: int) -> date:
    return date.today() - timedelta(days=n)


def add_expense(db, group, payer, description, rupees_paise, category, when, participants=None, custom=None, notes=None):
    if custom:
        shares = {user.id: amount for user, amount in custom}
        split_type = "custom"
    else:
        shares = split_equally(rupees_paise, [u.id for u in participants])
        split_type = "equal"
    assert sum(shares.values()) == rupees_paise
    expense = Expense(
        group_id=group.id, paid_by=payer.id, description=description, amount_paise=rupees_paise,
        category=category, split_type=split_type, expense_date=when, notes=notes,
        splits=[ExpenseSplit(user_id=uid, share_amount_paise=amt) for uid, amt in shares.items()],
    )
    db.add(expense)
    db.flush()


def main() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "sarvesh@example.com")):
            print("Seed data already present - nothing to do.")
            return

        password_hash = hash_password(PASSWORD)
        users = {}
        for name in ("Sarvesh", "Rahul", "Kiran", "Aman"):
            users[name] = User(name=name, email=f"{name.lower()}@example.com", password_hash=password_hash)
            db.add(users[name])
        db.flush()
        s, r, k, a = (users[n] for n in ("Sarvesh", "Rahul", "Kiran", "Aman"))

        room = Group(name="Room 204", created_by=s.id)
        room.members = [GroupMember(user_id=s.id, role="admin")] + [
            GroupMember(user_id=u.id, role="member") for u in (r, k, a)
        ]
        trip = Group(name="Goa Trip", created_by=r.id)
        trip.members = [GroupMember(user_id=r.id, role="admin")] + [
            GroupMember(user_id=u.id, role="member") for u in (s, k)
        ]
        db.add_all([room, trip])
        db.flush()

        everyone = [s, r, k, a]
        add_expense(db, room, s, "August rent", 2400000, "rent", days_ago(105), everyone)
        add_expense(db, room, k, "Monthly groceries", 365000, "groceries", days_ago(98), everyone)
        add_expense(db, room, r, "September rent", 2400000, "rent", days_ago(75), everyone)
        add_expense(db, room, a, "Weekend biryani", 128000, "food", days_ago(68), [r, k, a])
        add_expense(db, room, s, "October rent", 2400000, "rent", days_ago(45), everyone)
        add_expense(db, room, k, "Electricity bill", 235050, "utilities", days_ago(40), everyone,
                    notes="BESCOM bill for September")
        add_expense(db, room, r, "WiFi recharge", 79900, "utilities", days_ago(33), everyone)
        add_expense(db, room, s, "November rent", 2400000, "rent", days_ago(15), everyone)
        add_expense(db, room, s, "Groceries", 120000, "groceries", days_ago(9), everyone)
        add_expense(db, room, a, "Pizza night", 96000, "food", days_ago(6),
                    custom=[(a, 30000), (r, 30000), (k, 24000), (s, 12000)], notes="Sarvesh had one slice")
        add_expense(db, room, k, "Movie tickets", 105000, "entertainment", days_ago(3), [r, k, a])
        add_expense(db, room, r, "Auto to station", 18000, "transport", days_ago(1), [r, s])

        add_expense(db, trip, r, "Beach hotel (2 nights)", 900000, "rent", days_ago(60), [r, s, k])
        add_expense(db, trip, k, "Scooter rental", 150000, "transport", days_ago(59), [r, s, k])
        add_expense(db, trip, s, "Seafood dinner", 240000, "food", days_ago(59),
                    custom=[(s, 60000), (r, 100000), (k, 80000)])

        # One repayment in each group, sized from the real balances so it is valid.
        for group, payer, receiver, wanted in ((room, a, s, 500000), (trip, s, r, 100000)):
            nets = get_net_balances(db, group.id)
            amount = min(wanted, -nets[payer.id], nets[receiver.id])
            if amount > 0:
                db.add(Settlement(group_id=group.id, paid_by=payer.id, paid_to=receiver.id,
                                  amount_paise=amount, settled_at=days_ago(2)))

        db.commit()
        print("Seeded 4 users, 2 groups, 15 expenses and 2 settlements.")
        print(f"Log in with sarvesh@example.com / {PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
