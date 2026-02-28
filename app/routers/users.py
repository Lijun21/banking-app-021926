from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.user import UserResponse
from app.schemas.wallet import WalletResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/search", response_model=list[WalletResponse])
def search_user_wallets(
    username: str = Query(..., description="Exact username to look up"),
    db: Session = Depends(get_db),
    _current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Return wallets belonging to the given username (any authenticated user can call this)."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{username}' not found.")
    return db.query(Wallet).filter(Wallet.owner_id == user.id).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()
