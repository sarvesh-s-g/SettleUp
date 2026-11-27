from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.dependencies.auth import get_current_user, get_membership
from app.models import Expense, Group, GroupInvite, GroupMember, User
from app.models.group import INVITE_ACCEPTED, INVITE_DECLINED, INVITE_PENDING, ROLE_MEMBER
from app.schemas.group import GroupInviteOut, GroupSummary
from app.services.balance_service import get_user_net_balance, get_user_total_share

router = APIRouter(prefix="/invites", tags=["Invites"])


def query_invites_out(db: Session, *filters) -> list[GroupInviteOut]:
    """Fetch invites joined with group, invited user and inviter names."""
    invited_user = aliased(User)
    inviter = aliased(User)
    rows = db.execute(
        select(
            GroupInvite,
            Group.name.label("group_name"),
            invited_user.name.label("invited_user_name"),
            invited_user.email.label("invited_user_email"),
            inviter.name.label("invited_by_name"),
        )
        .join(Group, Group.id == GroupInvite.group_id)
        .join(invited_user, invited_user.id == GroupInvite.invited_user_id)
        .join(inviter, inviter.id == GroupInvite.invited_by)
        .where(*filters)
        .order_by(GroupInvite.created_at.desc(), GroupInvite.id.desc())
    ).all()
    return [
        GroupInviteOut(
            id=inv.id,
            group_id=inv.group_id,
            group_name=r.group_name,
            invited_user_id=inv.invited_user_id,
            invited_user_name=r.invited_user_name,
            invited_user_email=r.invited_user_email,
            invited_by_id=inv.invited_by,
            invited_by_name=r.invited_by_name,
            status=inv.status,
            created_at=inv.created_at,
            responded_at=inv.responded_at,
        )
        for r in rows
        for inv in (r.GroupInvite,)
    ]


def _get_my_pending_invite(db: Session, invite_id: int, user_id: int) -> GroupInvite:
    invite = db.scalar(
        select(GroupInvite)
        .where(GroupInvite.id == invite_id, GroupInvite.invited_user_id == user_id)
        .with_for_update()
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invite.status != INVITE_PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invitation has already been responded to")
    return invite


@router.get("", response_model=list[GroupInviteOut])
def list_my_invites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List pending group invitations for the logged-in user."""
    return query_invites_out(
        db,
        GroupInvite.invited_user_id == current_user.id,
        GroupInvite.status == INVITE_PENDING,
    )


@router.post("/{invite_id}/accept", response_model=GroupSummary)
def accept_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a group invitation and join the group as a member."""
    invite = _get_my_pending_invite(db, invite_id, current_user.id)
    if get_membership(db, invite.group_id, current_user.id) is None:
        db.add(GroupMember(group_id=invite.group_id, user_id=current_user.id, role=ROLE_MEMBER))

    invite.status = INVITE_ACCEPTED
    invite.responded_at = datetime.now(timezone.utc)
    db.commit()

    group = db.get(Group, invite.group_id)
    member_count = db.scalar(
        select(func.count(GroupMember.id)).where(GroupMember.group_id == group.id)
    )
    total_spending = db.scalar(
        select(func.coalesce(func.sum(Expense.amount_paise), 0)).where(
            Expense.group_id == group.id
        )
    )
    membership = get_membership(db, group.id, current_user.id)
    return GroupSummary(
        id=group.id,
        name=group.name,
        created_by=group.created_by,
        created_at=group.created_at,
        member_count=int(member_count or 0),
        total_spending_paise=int(total_spending or 0),
        my_share_paise=get_user_total_share(db, group.id, current_user.id),
        my_role=membership.role,
        my_balance_paise=get_user_net_balance(db, group.id, current_user.id),
    )


@router.post("/{invite_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decline a group invitation without joining the group."""
    invite = _get_my_pending_invite(db, invite_id, current_user.id)
    invite.status = INVITE_DECLINED
    invite.responded_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
