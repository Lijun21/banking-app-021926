import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IdempotencyRecord(Base):
    """Stores transfer responses keyed by (idempotency_key, user_id).

    When a client retries a POST /transfers with the same Idempotency-Key
    header, we return the cached response instead of executing the transfer
    again — preventing double-sends on network failures.
    """

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", "user_id", name="uq_idempotency_key_user"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
