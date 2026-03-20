import base64
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import CursorPage, QuoteRequest, TransactionResponse
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


@router.get("/wallets/{wallet_id}/transactions", response_model=CursorPage)
def get_wallet_transactions(
    wallet_id: str,
    cursor: str | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Return cursor-paginated transactions where the wallet was sender or receiver.

    Cursor encodes the created_at of the last returned item (base64 ISO string).
    Pass it back as ?cursor=... to fetch the next page.
    """
    q = db.query(Transaction).filter(
        (Transaction.from_wallet_id == wallet_id)
        | (Transaction.to_wallet_id == wallet_id)
    )

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(
                base64.b64decode(cursor.encode()).decode()
            ).replace(tzinfo=timezone.utc)
        except Exception:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid cursor")
        q = q.filter(Transaction.created_at < cursor_dt)

    # Fetch one extra to detect whether more pages exist
    rows = q.order_by(Transaction.created_at.desc()).limit(page_size + 1).all()
    has_more = len(rows) > page_size
    items = rows[:page_size]

    next_cursor: str | None = None
    if has_more and items:
        last_ts = items[-1].created_at
        next_cursor = base64.b64encode(last_ts.isoformat().encode()).decode()

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)

