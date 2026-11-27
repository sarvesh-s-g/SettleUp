from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    get_current_user, get_membership, require_group_admin, require_group_member,
)
from app.models import Expense, Group, GroupInvite, GroupMember, User
from app.models.group import INVITE_PENDING, ROLE_ADMIN, ROLE_MEMBER
from app.routers.invites import query_invites_out
from app.schemas.group import GroupCreate, GroupDetail, GroupInviteOut, GroupSummary, InviteMemberRequest, MemberOut
from app.services.balance_service import get_net_balances, get_user_net_balance

router = APIRouter(prefix="/groups", tags=["Groups"])


def _members_out(db: Session, group_id: int) -> list[MemberOut]:
    rows = db.execute(
        select(User.id, User.name, User.email, GroupMember.role, GroupMember.joined_at)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at, User.id)
    ).all()
    return [
        MemberOut(user_id=r.id, name=r.name, email=r.email, role=r.role, joined_at=r.joined_at)
        for r in rows
    ]


@router.post("", response_model=GroupDetail, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a group. The creator automatically becomes its admin (same transaction)."""
    group = Group(name=payload.name, created_by=current_user.id)
    group.members.append(GroupMember(user_id=current_user.id, role=ROLE_ADMIN))
    db.add(group)
    db.commit()  # INSERT into groups and group_members commit together
    return get_group(group.id, db, current_user)


@router.get("", response_model=list[GroupSummary])
def list_my_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List only the groups the logged-in user belongs to."""
    member_count = (
        select(GroupMember.group_id, func.count(GroupMember.id).label("member_count"))
        .group_by(GroupMember.group_id)
        .subquery()
    )
    rows = db.execute(
        select(Group, GroupMember.role, member_count.c.member_count)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .join(member_count, member_count.c.group_id == Group.id)
        .where(GroupMember.user_id == current_user.id)
        .order_by(Group.created_at.desc(), Group.id.desc())
    ).all()
    return [
        GroupSummary(
            id=group.id, name=group.name, created_by=group.created_by,
            created_at=group.created_at, member_count=count, my_role=role,
            my_balance_paise=get_user_net_balance(db, group.id, current_user.id),
        )
        for group, role, count in rows
    ]


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = require_group_member(db, group_id, current_user)
    group = db.get(Group, group_id)
    expense_count, total = db.execute(
        select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount_paise), 0))
        .where(Expense.group_id == group_id)
    ).one()
    members = _members_out(db, group_id)
    return GroupDetail(
        id=group.id, name=group.name, created_by=group.created_by,
        creator_name=group.creator.name, created_at=group.created_at,
        my_role=membership.role, member_count=len(members),
        expense_count=expense_count, total_spending_paise=int(total), members=members,
    )


@router.post("/{group_id}/invites", response_model=GroupInviteOut, status_code=status.HTTP_201_CREATED)
def invite_member(
    group_id: int,
    payload: InviteMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admins invite an already-registered user by email; the user must accept to join."""
    require_group_admin(db, group_id, current_user)
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No registered user has that email")
    if get_membership(db, group_id, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User is already a member of this group")

    existing_invite = db.scalar(
        select(GroupInvite).where(
            GroupInvite.group_id == group_id,
            GroupInvite.invited_user_id == user.id,
            GroupInvite.status == INVITE_PENDING,
        )
    )
    if existing_invite is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An invitation is already pending for this user")

    invite = GroupInvite(
        group_id=group_id,
        invited_user_id=user.id,
        invited_by=current_user.id,
        status=INVITE_PENDING,
    )
    db.add(invite)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An invitation is already pending for this user")

    return query_invites_out(db, GroupInvite.id == invite.id)[0]


@router.get("/{group_id}/invites", response_model=list[GroupInviteOut])
def list_group_invites(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List pending invitations for this group (admin only)."""
    require_group_admin(db, group_id, current_user)
    return query_invites_out(
        db,
        GroupInvite.group_id == group_id,
        GroupInvite.status == INVITE_PENDING,
    )


@router.delete("/{group_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_group_invite(
    group_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending invitation (admin only)."""
    require_group_admin(db, group_id, current_user)
    invite = db.scalar(
        select(GroupInvite).where(
            GroupInvite.id == invite_id,
            GroupInvite.group_id == group_id,
            GroupInvite.status == INVITE_PENDING,
        )
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pending invitation not found")
    db.delete(invite)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{group_id}/members", response_model=list[MemberOut])
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_group_member(db, group_id, current_user)
    return _members_out(db, group_id)


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member (admin) or leave the group (any member removing themselves).

    Rules: the member's balance must be zero, the last member cannot leave, and if
    the only admin leaves, the longest-standing remaining member becomes admin."""
    caller = require_group_member(db, group_id, current_user)
    if user_id != current_user.id and caller.role != ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only a group admin can remove other members")

    target = get_membership(db, group_id, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found in this group")

    members = db.scalars(
        select(GroupMember).where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at, GroupMember.id)
    ).all()
    if len(members) == 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The last member cannot leave the group")

    if get_net_balances(db, group_id).get(user_id, 0) != 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="This member has an unsettled balance. Settle up before removing them.",
        )

    others = [m for m in members if m.user_id != user_id]
    if target.role == ROLE_ADMIN and not any(m.role == ROLE_ADMIN for m in others):
        others[0].role = ROLE_ADMIN  # promote the earliest-joined remaining member

    db.delete(target)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a group (admin only), only allowed when all member balances are zero."""
    require_group_admin(db, group_id, current_user)
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if any(balance != 0 for balance in get_net_balances(db, group_id).values()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete group while members have unsettled balances. Settle up first.",
        )

    db.delete(group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
