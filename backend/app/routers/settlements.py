from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user, get_membership, require_group_member
from app.models import Group, Settlement, User
from app.models.group import ROLE_ADMIN
from app.schemas.settlement import (
    BalancesResponse, MemberBalance, SettlementCreate, SettlementOut, SuggestedSettlement,
    SuggestedSettlementsResponse,
)
from app.services.balance_service import compute_group_balances
from app.services.settlement_service import suggest_settlements

router = APIRouter(prefix="/groups/{group_id}", tags=["Balances & Settlements"])


def _settlement_out(s: Settlement) -> SettlementOut:
    return SettlementOut(
        id=s.id, group_id=s.group_id, paid_by=s.paid_by, paid_by_name=s.payer.name,
        paid_to=s.paid_to, paid_to_name=s.receiver.name, amount_paise=s.amount_paise,
        settled_at=s.settled_at, created_at=s.created_at,
    )


def _rupees(paise: int) -> str:
    return f"Rs {paise // 100}.{paise % 100:02d}"


@router.get("/balances", response_model=BalancesResponse)
def get_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_group_member(db, group_id, current_user)
    rows = compute_group_balances(db, group_id)
    return BalancesResponse(
        group_id=group_id,
        balances=[
            MemberBalance(
                user_id=r.user_id, name=r.name, is_member=r.is_member,
                total_paid_paise=r.total_paid_paise, total_share_paise=r.total_share_paise,
                settlements_paid_paise=r.settlements_paid_paise,
                settlements_received_paise=r.settlements_received_paise,
                net_balance_paise=r.net_balance_paise,
            )
            for r in rows
        ],
    )


@router.get("/settlements/suggested", response_model=SuggestedSettlementsResponse)
def get_suggested_settlements(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_group_member(db, group_id, current_user)
    rows = compute_group_balances(db, group_id)
    names = {r.user_id: r.name for r in rows}
    plan = suggest_settlements({r.user_id: r.net_balance_paise for r in rows})
    return SuggestedSettlementsResponse(
        group_id=group_id,
        settlements=[
            SuggestedSettlement(
                from_user_id=debtor, from_name=names[debtor],
                to_user_id=creditor, to_name=names[creditor], amount_paise=amount,
            )
            for debtor, creditor, amount in plan
        ],
    )


@router.post("/settlements", response_model=SettlementOut, status_code=status.HTTP_201_CREATED)
def record_settlement(
    group_id: int,
    payload: SettlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a repayment that happened outside the app (cash, UPI, ...)."""
    caller = require_group_member(db, group_id, current_user)
    if current_user.id not in (payload.paid_by, payload.paid_to) and caller.role != ROLE_ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only the payer, the receiver or a group admin can record this settlement",
        )
    if get_membership(db, group_id, payload.paid_by) is None or get_membership(db, group_id, payload.paid_to) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Payer and receiver must both be group members")

    # Lock this group's row until COMMIT. A second settlement request for the same
    # group waits here, so both requests cannot validate against the same old
    # balances and together over-settle a debt.
    db.execute(select(Group.id).where(Group.id == group_id).with_for_update())

    balances = {r.user_id: r.net_balance_paise for r in compute_group_balances(db, group_id)}
    owes = -balances.get(payload.paid_by, 0)        # how much the payer still owes
    is_owed = balances.get(payload.paid_to, 0)      # how much the receiver is still owed
    if owes <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The payer does not owe anything in this group")
    if is_owed <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The receiver is not owed anything in this group")
    limit = min(owes, is_owed)
    if payload.amount_paise > limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Amount is more than the outstanding balance. Maximum allowed is {_rupees(limit)}.",
        )

    settlement = Settlement(
        group_id=group_id, paid_by=payload.paid_by, paid_to=payload.paid_to,
        amount_paise=payload.amount_paise, settled_at=payload.settled_at or date.today(),
    )
    db.add(settlement)
    db.commit()  # releases the row lock
    db.refresh(settlement)
    return _settlement_out(settlement)


@router.get("/settlements", response_model=list[SettlementOut])
def list_settlements(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_group_member(db, group_id, current_user)
    settlements = db.scalars(
        select(Settlement)
        .where(Settlement.group_id == group_id)
        .options(selectinload(Settlement.payer), selectinload(Settlement.receiver))
        .order_by(Settlement.settled_at.desc(), Settlement.id.desc())
    ).all()
    return [_settlement_out(s) for s in settlements]
