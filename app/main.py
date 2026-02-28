from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth_router, users_router, wallets_router, transactions_router

# Create all tables on startup (use Alembic migrations in production)
# Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    Base.metadata.create_all(bind=engine)
    yield
    # Runs on shutdown (optional cleanup)

app = FastAPI(
    title="Banking App",
    description="Transfer money between wallets across USD, EUR, GBP, and BTC.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",  # any localhost port (dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(wallets_router)
app.include_router(transactions_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
