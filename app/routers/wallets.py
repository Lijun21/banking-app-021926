from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate, WalletResponse

router = APIRouter(prefix="/users/{user_id}/wallets", tags=["Wallets"])


def _require_self(user_id: str, current_user: User) -> None:
    """Raise 403 if the authenticated user is not the owner referenced in the URL."""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: you can only manage your own wallets.",
        )


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
def create_wallet(
    user_id: str,
    payload: WalletCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    _require_self(user_id, current_user)

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
def list_wallets(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    _require_self(user_id, current_user)

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return db.query(Wallet).filter(Wallet.owner_id == user_id).all()


@router.get("/{wallet_id}", response_model=WalletResponse)
def get_wallet(
    user_id: str,
    wallet_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    _require_self(user_id, current_user)

    wallet = db.get(Wallet, wallet_id)
    if wallet is None or wallet.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found.")
    return wallet
