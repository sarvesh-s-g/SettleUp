"""FastAPI dependencies for authentication (who are you?) and group authorization
(are you allowed to touch this group?)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Group, GroupMember, User
from app.models.group import ROLE_ADMIN
from app.utils.security import decode_access_token

# auto_error=False so we can return our own 401 message instead of FastAPI's 403.
bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token from /auth/login")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Read 'Authorization: Bearer <token>', validate the JWT and load the user."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def get_membership(db: Session, group_id: int, user_id: int) -> GroupMember | None:
    return db.scalar(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )


def require_group_member(db: Session, group_id: int, user: User) -> GroupMember:
    """Return the caller's membership row, or 404 if the group does not exist OR the
    caller is not a member. Using 404 for both means outsiders cannot even learn
    whether a group id exists."""
    membership = get_membership(db, group_id, user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return membership


def require_group_admin(db: Session, group_id: int, user: User) -> GroupMember:
    membership = require_group_member(db, group_id, user)
    if membership.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a group admin can perform this action",
        )
    return membership


def get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group
