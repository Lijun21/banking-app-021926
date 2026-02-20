from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransferRequest, TransactionResponse
from app.services.transfer_service import transfer

router = APIRouter(tags=["Transactions"])


@router.post("/transfers", response_model=TransactionResponse, status_code=201)
def make_transfer(payload: TransferRequest, db: Session = Depends(get_db)):
    return transfer(
        db=db,
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=payload.to_wallet_id,
        amount=payload.amount,
        note=payload.note,
    )


@router.get("/wallets/{wallet_id}/transactions", response_model=list[TransactionResponse])
def get_wallet_transactions(
    wallet_id: str,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
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
