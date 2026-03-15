import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, Enum as SAEnum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.currency import Currency

QUOTE_TTL_SECONDS = 60


class TransferStatus:
    QUOTE_LOCKED = "quote_locked"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    from_wallet_id: Mapped[str] = mapped_column(ForeignKey("wallets.id"), nullable=False)
    to_wallet_id: Mapped[str] = mapped_column(ForeignKey("wallets.id"), nullable=False)

    # Amount in the source wallet's currency
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=28, scale=8), nullable=False)
    currency: Mapped[Currency] = mapped_column(SAEnum(Currency, name="currency_enum"), nullable=False)

    # Locked rate and calculated receive amount (set at quote_locked stage)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(precision=28, scale=8), nullable=True)
    receive_amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=28, scale=8), nullable=True)

    # State machine: quote_locked → completed | failed | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TransferStatus.QUOTE_LOCKED)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(seconds=QUOTE_TTL_SECONDS),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    from_wallet: Mapped["Wallet"] = relationship(  # noqa: F821
        "Wallet", foreign_keys=[from_wallet_id], back_populates="sent_transactions"
    )
    to_wallet: Mapped["Wallet"] = relationship(  # noqa: F821
        "Wallet", foreign_keys=[to_wallet_id], back_populates="received_transactions"
    )
