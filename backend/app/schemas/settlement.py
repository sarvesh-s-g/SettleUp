from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.expense import MAX_AMOUNT_PAISE


class SettlementCreate(BaseModel):
    paid_by: int
    paid_to: int
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE, examples=[35000])
    settled_at: date | None = None  # defaults to today on the server

    @model_validator(mode="after")
    def different_people(self):
        if self.paid_by == self.paid_to:
            raise ValueError("Payer and receiver must be different people")
        return self


class SettlementOut(BaseModel):
    id: int
    group_id: int
    paid_by: int
    paid_by_name: str
    paid_to: int
    paid_to_name: str
    amount_paise: int
    settled_at: date
    created_at: datetime


class MemberBalance(BaseModel):
    user_id: int
    name: str
    is_member: bool
    total_paid_paise: int
    total_share_paise: int
    settlements_paid_paise: int
    settlements_received_paise: int
    net_balance_paise: int


class BalancesResponse(BaseModel):
    group_id: int
    balances: list[MemberBalance]


class SuggestedSettlement(BaseModel):
    from_user_id: int
    from_name: str
    to_user_id: int
    to_name: str
    amount_paise: int


class SuggestedSettlementsResponse(BaseModel):
    group_id: int
    settlements: list[SuggestedSettlement]
