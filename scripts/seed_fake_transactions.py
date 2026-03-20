"""
Seed fake transactions for lucy@gmail.com so pagination can be tested in the UI.

Usage:
    python3 scripts/seed_fake_transactions.py

Behaviour:
- Finds (or creates) the user lily@gmail.com with a USD wallet.
- Ensures a second "counterparty" user exists with a USD wallet to be the other side
  of every transaction.
- Inserts 50 completed transactions (mix of sent/received) with varied amounts, notes,
  and timestamps spread over the last 30 days.
"""

import sys
import os
import uuid
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Allow running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransferStatus
from app.models.currency import Currency
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

LUCY_EMAIL = "lucy@gmail.com"
LUCY_USERNAME = "lucy"
LUCY_PASSWORD = "password123"

COUNTER_EMAIL = "bob@example.com"
COUNTER_USERNAME = "bob"
COUNTER_PASSWORD = "password123"

NUM_TRANSACTIONS = 50

NOTES = [
    "Rent payment", "Dinner split", "Gift", "Loan repayment",
    "Groceries", "Utilities", "Concert tickets", "Coffee ☕",
    "Birthday present", "Hotel booking", None,
]


def get_or_create_user(db: Session, email: str, username: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"  Found user: {email} (id={user.id})")
        return user
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=pwd_ctx.hash(password),
    )
    db.add(user)
    db.flush()
    print(f"  Created user: {email} (id={user.id})")
    return user


def get_or_create_wallet(db: Session, owner: User, currency: Currency) -> Wallet:
    wallet = db.query(Wallet).filter(
        Wallet.owner_id == owner.id,
        Wallet.currency == currency,
    ).first()
    if wallet:
        print(f"  Found wallet: {currency} for {owner.email} (id={wallet.id})")
        return wallet
    wallet = Wallet(
        id=str(uuid.uuid4()),
        owner_id=owner.id,
        currency=currency,
        balance=Decimal("10000.00"),
    )
    db.add(wallet)
    db.flush()
    print(f"  Created wallet: {currency} for {owner.email} (id={wallet.id})")
    return wallet


def seed(db: Session):
    print("\n--- Users ---")
    lucy = get_or_create_user(db, LUCY_EMAIL, LUCY_USERNAME, LUCY_PASSWORD)
    bob = get_or_create_user(db, COUNTER_EMAIL, COUNTER_USERNAME, COUNTER_PASSWORD)

    print("\n--- Wallets ---")
    lucy_usd = get_or_create_wallet(db, lucy, Currency.USD)
    bob_usd = get_or_create_wallet(db, bob, Currency.USD)

    print(f"\n--- Inserting {NUM_TRANSACTIONS} transactions ---")
    now = datetime.now(timezone.utc)
    for i in range(NUM_TRANSACTIONS):
        # Alternate sent/received so both directions appear
        if i % 2 == 0:
            from_wallet, to_wallet = lucy_usd, bob_usd
        else:
            from_wallet, to_wallet = bob_usd, lucy_usd

        amount = Decimal(str(round(random.uniform(5, 500), 2)))
        created_at = now - timedelta(days=random.uniform(0, 30))
        completed_at = created_at + timedelta(seconds=random.randint(1, 10))

        txn = Transaction(
            id=str(uuid.uuid4()),
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            amount=amount,
            currency=Currency.USD,
            rate=Decimal("1.0"),
            receive_amount=amount,
            status=TransferStatus.COMPLETED,
            note=random.choice(NOTES),
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=60),
            completed_at=completed_at,
        )
        db.add(txn)

    db.commit()
    print(f"\n✓ Done. {NUM_TRANSACTIONS} transactions seeded for {LUCY_EMAIL}.")
    print(f"  Login credentials:  {LUCY_EMAIL} / {LUCY_PASSWORD}")
    print(f"  Wallet ID (USD):    {lucy_usd.id}")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
