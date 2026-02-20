from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator

from app.models.currency import Currency


class TransferRequest(BaseModel):
    from_wallet_id: str
    to_wallet_id: str
    amount: Decimal
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Transfer amount must be positive")
        return v


class TransactionResponse(BaseModel):
    id: str
    from_wallet_id: str
    to_wallet_id: str
    amount: Decimal
    currency: Currency
    status: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
