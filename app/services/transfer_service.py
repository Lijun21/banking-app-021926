from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransferStatus
from app.services.currency_service import RATES_TO_USD, convert


def lock_quote(
    db: Session,
    from_wallet_id: str,
    to_wallet_id: str,
    amount: Decimal,
    requester_id: str,
    note: str | None = None,
) -> Transaction:
    """
    Stage 1 — Create a transfer row with status=quote_locked.
    Validates wallets and balance, locks the rate, sets expires_at.
    No money moves yet.
    """
    if from_wallet_id == to_wallet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same wallet.",
        )

    from_wallet = db.get(Wallet, from_wallet_id)
    if from_wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source wallet not found.")
    if from_wallet.owner_id != requester_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: you do not own the source wallet.")

    to_wallet = db.get(Wallet, to_wallet_id)
    if to_wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination wallet not found.")

    if from_wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Available: {from_wallet.balance} {from_wallet.currency}",
        )

    # Calculate rate and receive amount
    from_cur = from_wallet.currency
    to_cur = to_wallet.currency
    if from_cur == to_cur:
        receive_amount = amount
        rate = Decimal("1")
    else:
        in_usd = amount * RATES_TO_USD[from_cur]
        receive_amount = (in_usd / RATES_TO_USD[to_cur]).quantize(Decimal("0.00000001"))
        rate = (RATES_TO_USD[from_cur] / RATES_TO_USD[to_cur]).quantize(Decimal("0.00000001"))

    txn = Transaction(
        from_wallet_id=from_wallet_id,
        to_wallet_id=to_wallet_id,
        amount=amount,
        currency=from_cur,
        rate=rate,
        receive_amount=receive_amount,
        status=TransferStatus.QUOTE_LOCKED,
        note=note,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def confirm_transfer(
    db: Session,
    transfer_id: str,
    requester_id: str,
) -> Transaction:
    """
    Stage 2 — Confirm a quote_locked transfer.
    Validates ownership, expiry, and status; then executes the balance transfer.
    Uses SELECT FOR UPDATE to prevent concurrent double-execution.
    """
    txn: Transaction | None = (
        db.query(Transaction)
        .filter(Transaction.id == transfer_id)
        .with_for_update()
        .first()
    )

    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")

    # Ownership: verify via source wallet
    from_wallet = db.get(Wallet, txn.from_wallet_id)
    if from_wallet is None or from_wallet.owner_id != requester_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    # Idempotency: already completed, return as-is
    if txn.status == TransferStatus.COMPLETED:
        return txn

    # State guard
    if txn.status != TransferStatus.QUOTE_LOCKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transfer cannot be confirmed (status: {txn.status}).",
        )

    # Expiry check
    if datetime.now(timezone.utc) > txn.expires_at:
        txn.status = TransferStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Quote has expired. Please request a new quote.",
        )

    # Lock wallets in consistent order to prevent deadlock
    lock_ids = sorted([txn.from_wallet_id, txn.to_wallet_id])
    locked = db.query(Wallet).filter(Wallet.id.in_(lock_ids)).with_for_update().all()
    wallet_map = {w.id: w for w in locked}
    from_w = wallet_map[txn.from_wallet_id]
    to_w = wallet_map[txn.to_wallet_id]

    if from_w.balance < txn.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Available: {from_w.balance} {from_w.currency}",
        )

    # Execute balance transfer using the locked rate
    from_w.balance -= txn.amount
    to_w.balance += txn.receive_amount

    txn.status = TransferStatus.COMPLETED
    txn.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(txn)
    return txn
