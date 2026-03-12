import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.idempotency import IdempotencyRecord
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransferRequest, TransactionResponse
from app.services.transfer_service import transfer

router = APIRouter(tags=["Transactions"])


@router.post("/transfers", response_model=TransactionResponse, status_code=201)
def make_transfer(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    # If client sent an idempotency key, check for a cached result first
    if idempotency_key:
        existing = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.user_id == current_user.id,
        ).first()
        if existing:
            return Response(
                content=existing.response_json,
                status_code=existing.status_code,
                media_type="application/json",
            )

    txn = transfer(
        db=db,
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=payload.to_wallet_id,
        amount=payload.amount,
        requester_id=current_user.id,
        note=payload.note,
    )

    # Cache the result so retries with the same key get the same response
    if idempotency_key:
        response_data = TransactionResponse.model_validate(txn).model_dump(mode="json")
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            status_code=201,
            response_json=json.dumps(response_data),
        )
        db.add(record)
        db.commit()

    return txn


@router.get("/wallets/{wallet_id}/transactions", response_model=list[TransactionResponse])
def get_wallet_transactions(
    wallet_id: str,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Return all transactions where the wallet was sender or receiver."""
    txns = (
        db.query(Transaction)
        .filter(
            (Transaction.from_wallet_id == wallet_id)
            | (Transaction.to_wallet_id == wallet_id)
        )
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return txns
