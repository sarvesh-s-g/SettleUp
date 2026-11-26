from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Room 204"])

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name cannot be blank")
        return value


class AddMemberRequest(BaseModel):
    email: EmailStr = Field(examples=["rahul@example.com"])

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    role: str
    joined_at: datetime


class GroupSummary(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime
    member_count: int
    my_role: str
    my_balance_paise: int


class GroupDetail(BaseModel):
    id: int
    name: str
    created_by: int
    creator_name: str
    created_at: datetime
    my_role: str
    member_count: int
    expense_count: int
    total_spending_paise: int
    members: list[MemberOut]
