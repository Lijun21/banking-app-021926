from fastapi import FastAPI

from app.database import Base, engine
from app.routers import users_router, wallets_router, transactions_router

# Create all tables on startup (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Banking App",
    description="Transfer money between wallets across USD, EUR, GBP, and BTC.",
    version="1.0.0",
)

app.include_router(users_router)
app.include_router(wallets_router)
app.include_router(transactions_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
