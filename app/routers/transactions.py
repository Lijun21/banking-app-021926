import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    PaginatedTransactionResponse,
    QuoteRequest,
    TransactionResponse,
)
from app.services.transfer_service import lock_quote, confirm_transfer

router = APIRouter(tags=["Transactions"])


@router.post("/transfers", response_model=TransactionResponse, status_code=201)
def create_transfer(
    payload: QuoteRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Stage 1: validate, lock rate, persist transfer with status=quote_locked."""
    return lock_quote(
        db=db,
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=payload.to_wallet_id,
        amount=payload.amount,
        requester_id=current_user.id,
        note=payload.note,
    )


@router.post("/transfers/{transfer_id}/confirm", response_model=TransactionResponse)
def confirm_transfer_endpoint(
    transfer_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Stage 2: verify quote not expired, execute balance transfer, status=completed."""
    return confirm_transfer(db=db, transfer_id=transfer_id, requester_id=current_user.id)


@router.get("/wallets/{wallet_id}/transactions", response_model=PaginatedTransactionResponse)
def get_wallet_transactions(
    wallet_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Return paginated transactions where the wallet was sender or receiver."""
    base_q = db.query(Transaction).filter(
        (Transaction.from_wallet_id == wallet_id)
        | (Transaction.to_wallet_id == wallet_id)
    )
    total = base_q.count()
    items = (
        base_q
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedTransactionResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 1,
    )

