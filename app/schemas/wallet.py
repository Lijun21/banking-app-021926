from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator

from app.models.currency import Currency


class WalletCreate(BaseModel):
    currency: Currency
    initial_balance: Decimal = Decimal("0")

    @field_validator("initial_balance")
    @classmethod
    def balance_must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Initial balance cannot be negative")
        return v


class WalletResponse(BaseModel):
    id: str
    owner_id: str
    currency: Currency
    balance: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
