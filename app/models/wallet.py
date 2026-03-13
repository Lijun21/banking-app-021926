import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Numeric, ForeignKey, Enum as SAEnum, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.database import Base
from app.models.currency import Currency


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("owner_id", "currency", name="uq_wallet_owner_currency"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency_enum"), nullable=False
    )
    # Use Numeric(precision=28, scale=8) to safely handle both fiat and crypto amounts
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=28, scale=8), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    owner: Mapped["User"] = relationship("User", back_populates="wallets")  # noqa: F821
    sent_transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction", foreign_keys="Transaction.from_wallet_id", back_populates="from_wallet"
    )
    received_transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction", foreign_keys="Transaction.to_wallet_id", back_populates="to_wallet"
    )
