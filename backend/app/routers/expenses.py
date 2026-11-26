from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user, get_membership, require_group_member
from app.models import Expense, ExpenseSplit, GroupMember, User
from app.models.group import ROLE_ADMIN
from app.schemas.expense import (
    Category, ExpenseCreate, ExpenseListResponse, ExpenseOut, ExpenseUpdate, SplitOut,
    validate_split_definition,
)
from app.services.split_service import custom_shares, split_equally

router = APIRouter(tags=["Expenses"])


# ---------------------------------------------------------------- helpers

def expense_to_out(expense: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id, group_id=expense.group_id, description=expense.description,
        amount_paise=expense.amount_paise, category=expense.category,
        split_type=expense.split_type, notes=expense.notes, expense_date=expense.expense_date,
        paid_by=expense.paid_by, paid_by_name=expense.payer.name,
        splits=[
            SplitOut(user_id=s.user_id, user_name=s.user.name, share_amount_paise=s.share_amount_paise)
            for s in expense.splits
        ],
        created_at=expense.created_at, updated_at=expense.updated_at,
    )


def _load_expense(db: Session, expense_id: int) -> Expense | None:
    # selectinload fetches payer, splits and split users in a few extra queries
    # instead of one query per split (avoids the "N+1 queries" problem).
    return db.scalar(
        select(Expense)
        .where(Expense.id == expense_id)
        .options(
            selectinload(Expense.payer),
            selectinload(Expense.splits).selectinload(ExpenseSplit.user),
        )
    )


def _member_ids(db: Session, group_id: int) -> set[int]:
    return set(db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id)).all())


def _check_people_are_members(db: Session, group_id: int, paid_by: int, participant_ids) -> None:
    members = _member_ids(db, group_id)
    if paid_by not in members:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The payer must be a member of the group")
    outsiders = set(participant_ids) - members
    if outsiders:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"These participants are not group members: {sorted(outsiders)}",
        )


def _build_shares(amount_paise: int, split_type: str, participant_ids, splits) -> dict[int, int]:
    if split_type == "equal":
        return split_equally(amount_paise, list(participant_ids))
    return custom_shares(amount_paise, [(s.user_id, s.share_amount_paise) for s in splits])


def _get_expense_for_member(db: Session, expense_id: int, user: User) -> tuple[Expense, GroupMember]:
    """Load an expense and make sure the caller belongs to its group.
    Non-members get 404 so they cannot tell whether the expense exists."""
    expense = _load_expense(db, expense_id)
    membership = get_membership(db, expense.group_id, user.id) if expense else None
    if expense is None or membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense, membership


def _require_can_modify(expense: Expense, membership: GroupMember, user: User) -> None:
    if expense.paid_by != user.id and membership.role != ROLE_ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only the person who paid or a group admin can change this expense",
        )


# ---------------------------------------------------------------- endpoints

@router.post(
    "/groups/{group_id}/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED
)
def create_expense(
    group_id: int,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_group_member(db, group_id, current_user)
    participant_ids = (
        payload.participant_ids if payload.split_type == "equal"
        else [s.user_id for s in payload.splits]
    )
    _check_people_are_members(db, group_id, payload.paid_by, participant_ids)
    shares = _build_shares(payload.amount_paise, payload.split_type, payload.participant_ids, payload.splits)

    expense = Expense(
        group_id=group_id, paid_by=payload.paid_by, description=payload.description,
        amount_paise=payload.amount_paise, category=payload.category,
        split_type=payload.split_type, notes=payload.notes, expense_date=payload.expense_date,
    )
    # Splits are attached to the expense object, so SQLAlchemy inserts the expense
    # first (to get its id) and then the splits - all inside ONE transaction.
    expense.splits = [ExpenseSplit(user_id=uid, share_amount_paise=amt) for uid, amt in shares.items()]
    db.add(expense)
    db.commit()
    return expense_to_out(_load_expense(db, expense.id))


@router.get("/groups/{group_id}/expenses", response_model=ExpenseListResponse)
def list_expenses(
    group_id: int,
    category: Category | None = Query(default=None),
    member_id: int | None = Query(default=None, description="Expenses this user paid for or shares in"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_group_member(db, group_id, current_user)
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="from_date must be before to_date")

    conditions = [Expense.group_id == group_id]
    if category:
        conditions.append(Expense.category == category)
    if from_date:
        conditions.append(Expense.expense_date >= from_date)
    if to_date:
        conditions.append(Expense.expense_date <= to_date)
    if member_id is not None:
        shares_in = select(ExpenseSplit.expense_id).where(ExpenseSplit.user_id == member_id)
        conditions.append(or_(Expense.paid_by == member_id, Expense.id.in_(shares_in)))

    total = db.scalar(select(func.count(Expense.id)).where(*conditions))
    expenses = db.scalars(
        select(Expense)
        .where(*conditions)
        .options(selectinload(Expense.payer), selectinload(Expense.splits).selectinload(ExpenseSplit.user))
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ExpenseListResponse(
        items=[expense_to_out(e) for e in expenses], total=total, page=page, page_size=page_size
    )


@router.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense, _ = _get_expense_for_member(db, expense_id, current_user)
    return expense_to_out(expense)


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense, membership = _get_expense_for_member(db, expense_id, current_user)
    _require_can_modify(expense, membership, current_user)

    sent = payload.model_fields_set
    for field in ("description", "category", "expense_date", "notes"):
        if field in sent:
            value = getattr(payload, field)
            if value is None and field != "notes":
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be null")
            setattr(expense, field, value.strip() if field == "description" else value)

    new_paid_by = payload.paid_by if "paid_by" in sent and payload.paid_by is not None else expense.paid_by
    participant_ids = [s.user_id for s in expense.splits]

    if payload.changes_split:
        amount = payload.amount_paise if payload.amount_paise is not None else expense.amount_paise
        try:
            validate_split_definition(amount, payload.split_type, payload.participant_ids, payload.splits)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
        participant_ids = (
            payload.participant_ids if payload.split_type == "equal"
            else [s.user_id for s in payload.splits]
        )

    _check_people_are_members(db, expense.group_id, new_paid_by, participant_ids)
    expense.paid_by = new_paid_by

    if payload.changes_split:
        expense.amount_paise = amount
        expense.split_type = payload.split_type
        shares = _build_shares(amount, payload.split_type, payload.participant_ids, payload.splits)
        # Delete the old split rows first, then insert the new ones. Flushing in
        # between avoids a temporary clash with UNIQUE(expense_id, user_id).
        expense.splits.clear()
        db.flush()
        expense.splits.extend(
            ExpenseSplit(user_id=uid, share_amount_paise=amt) for uid, amt in shares.items()
        )

    db.commit()  # all changes (expense row + old/new splits) commit atomically
    db.expire_all()
    return expense_to_out(_load_expense(db, expense.id))


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense, membership = _get_expense_for_member(db, expense_id, current_user)
    _require_can_modify(expense, membership, current_user)
    db.delete(expense)  # its expense_splits rows are deleted by the cascade
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
