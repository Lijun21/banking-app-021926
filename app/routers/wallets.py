from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate, WalletResponse

router = APIRouter(prefix="/users/{user_id}/wallets", tags=["Wallets"])


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
def create_wallet(user_id: str, payload: WalletCreate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # One wallet per currency per user
    existing = db.query(Wallet).filter(
        Wallet.owner_id == user_id,
        Wallet.currency == payload.currency,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has a {payload.currency} wallet.",
        )

    wallet = Wallet(
        owner_id=user_id,
        currency=payload.currency,
        balance=payload.initial_balance,
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


@router.get("/", response_model=list[WalletResponse])
def list_wallets(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return db.query(Wallet).filter(Wallet.owner_id == user_id).all()


@router.get("/{wallet_id}", response_model=WalletResponse)
def get_wallet(user_id: str, wallet_id: str, db: Session = Depends(get_db)):
    wallet = db.get(Wallet, wallet_id)
    if wallet is None or wallet.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found.")
    return wallet
