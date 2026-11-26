"""Expense schemas. All money fields are integers in paise (1 rupee = 100 paise)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Category = Literal[
    "food", "groceries", "rent", "utilities", "transport", "entertainment", "shopping", "other"
]
SplitType = Literal["equal", "custom"]

# Rs 1 crore. A sanity limit so a typo cannot create an absurd expense.
MAX_AMOUNT_PAISE = 1_000_000_000


class SplitIn(BaseModel):
    user_id: int
    share_amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)


def validate_split_definition(amount_paise, split_type, participant_ids, splits) -> None:
    """Shared rules for create and update. Raises ValueError with a readable message."""
    if split_type == "equal":
        if not participant_ids:
            raise ValueError("Select at least one participant for an equal split")
        if len(set(participant_ids)) != len(participant_ids):
            raise ValueError("A participant is listed more than once")
        if amount_paise < len(participant_ids):
            raise ValueError("Amount is too small to split between that many people")
    else:  # custom
        if not splits:
            raise ValueError("Provide at least one share for a custom split")
        user_ids = [s.user_id for s in splits]
        if len(set(user_ids)) != len(user_ids):
            raise ValueError("A participant is listed more than once")
        total = sum(s.share_amount_paise for s in splits)
        if total != amount_paise:
            raise ValueError(
                f"Custom shares add up to {total} paise but the expense is {amount_paise} paise"
            )


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200, examples=["Groceries"])
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE, examples=[120000])
    paid_by: int
    category: Category = "other"
    expense_date: date
    notes: str | None = Field(default=None, max_length=1000)
    split_type: SplitType
    # Used when split_type == "equal"
    participant_ids: list[int] | None = None
    # Used when split_type == "custom"
    splits: list[SplitIn] | None = None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be blank")
        return value

    @model_validator(mode="after")
    def check_split(self):
        validate_split_definition(
            self.amount_paise, self.split_type, self.participant_ids, self.splits
        )
        return self


class ExpenseUpdate(BaseModel):
    """PATCH body. Every field is optional.

    If any of amount_paise / split_type / participant_ids / splits is sent, the split
    is rebuilt, so split_type plus participant_ids (equal) or splits (custom) must be
    sent together."""

    description: str | None = Field(default=None, min_length=1, max_length=200)
    amount_paise: int | None = Field(default=None, gt=0, le=MAX_AMOUNT_PAISE)
    paid_by: int | None = None
    category: Category | None = None
    expense_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)
    split_type: SplitType | None = None
    participant_ids: list[int] | None = None
    splits: list[SplitIn] | None = None

    @property
    def changes_split(self) -> bool:
        return any(
            f in self.model_fields_set
            for f in ("amount_paise", "split_type", "participant_ids", "splits")
        )

    @model_validator(mode="after")
    def check_split_fields(self):
        if self.changes_split and self.split_type is None:
            raise ValueError("split_type is required when changing the amount or the split")
        return self


class SplitOut(BaseModel):
    user_id: int
    user_name: str
    share_amount_paise: int


class ExpenseOut(BaseModel):
    id: int
    group_id: int
    description: str
    amount_paise: int
    category: str
    split_type: str
    notes: str | None
    expense_date: date
    paid_by: int
    paid_by_name: str
    splits: list[SplitOut]
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    items: list[ExpenseOut]
    total: int
    page: int
    page_size: int
