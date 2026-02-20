from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.currency import Currency
from app.services.currency_service import convert


def transfer(
    db: Session,
    from_wallet_id: str,
    to_wallet_id: str,
    amount: Decimal,
    note: str | None = None,
) -> Transaction:
    """
    Transfer `amount` (in the source wallet's currency) from one wallet to another.
    - Same currency: direct debit/credit.
    - Different currencies: convert via hard-coded exchange rates.
    Raises HTTP 400/404 on invalid inputs.
    """
    if from_wallet_id == to_wallet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same wallet.",
        )

    # SELECT FOR UPDATE locks both rows for the duration of this transaction,
    # preventing concurrent transfers on the same wallet.(Race condition)

    # Always lock in a consistent ID order to avoid deadlocks between two
    # transfers that involve the same pair of wallets in opposite directions.
    # (Alice pays Bob, Bob pays Alice — simultaneously)
    lock_ids = sorted([from_wallet_id, to_wallet_id])
    locked = (
        db.query(Wallet)
        .filter(Wallet.id.in_(lock_ids))
        .with_for_update()
        .all()
    )
    wallet_map = {w.id: w for w in locked}
    from_wallet: Wallet | None = wallet_map.get(from_wallet_id)
    to_wallet: Wallet | None = wallet_map.get(to_wallet_id)

    if from_wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source wallet not found.")
    if to_wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination wallet not found.")

    if from_wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Available: {from_wallet.balance} {from_wallet.currency}",
        )

    # Debit source
    from_wallet.balance -= amount

    # Credit destination (convert if currencies differ)
    credit_amount: Decimal = convert(amount, from_wallet.currency, to_wallet.currency)
    to_wallet.balance += credit_amount

    transaction = Transaction(
        from_wallet_id=from_wallet_id,
        to_wallet_id=to_wallet_id,
        amount=amount,
        currency=from_wallet.currency,
        status="completed",
        note=note,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction
