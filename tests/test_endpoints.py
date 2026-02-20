"""
Integration-style tests for the transaction and transfer endpoints.
Uses an in-memory SQLite database so no Docker is needed to run tests.
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# Use SQLite in-memory for tests
SQLITE_URL = "sqlite:///./test.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def two_users_with_wallets(client):
    """Create two users each with a USD wallet and seed balances."""
    alice = client.post("/users/", json={"username": "alice", "email": "alice@example.com"}).json()
    bob = client.post("/users/", json={"username": "bob", "email": "bob@example.com"}).json()

    alice_wallet = client.post(
        f"/users/{alice['id']}/wallets/",
        json={"currency": "USD", "initial_balance": "500"},
    ).json()
    bob_wallet = client.post(
        f"/users/{bob['id']}/wallets/",
        json={"currency": "USD", "initial_balance": "100"},
    ).json()

    return alice, bob, alice_wallet, bob_wallet


# ---------------------------------------------------------------------------
# User endpoint tests
# ---------------------------------------------------------------------------

class TestUserEndpoints:
    def test_create_user(self, client):
        response = client.post("/users/", json={"username": "carol", "email": "carol@test.com"})
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "carol"
        assert "id" in data

    def test_duplicate_user_returns_409(self, client):
        client.post("/users/", json={"username": "dave", "email": "dave@test.com"})
        response = client.post("/users/", json={"username": "dave", "email": "dave@test.com"})
        assert response.status_code == 409

    def test_get_user(self, client):
        created = client.post("/users/", json={"username": "eve", "email": "eve@test.com"}).json()
        response = client.get(f"/users/{created['id']}")
        assert response.status_code == 200
        assert response.json()["username"] == "eve"

    def test_get_nonexistent_user_returns_404(self, client):
        response = client.get("/users/does-not-exist")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Wallet endpoint tests
# ---------------------------------------------------------------------------

class TestWalletEndpoints:
    def test_create_wallet(self, client):
        user = client.post("/users/", json={"username": "frank", "email": "frank@test.com"}).json()
        response = client.post(
            f"/users/{user['id']}/wallets/",
            json={"currency": "BTC", "initial_balance": "0.5"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "BTC"
        assert Decimal(data["balance"]) == Decimal("0.5")

    def test_duplicate_currency_wallet_returns_409(self, client):
        user = client.post("/users/", json={"username": "grace", "email": "grace@test.com"}).json()
        client.post(f"/users/{user['id']}/wallets/", json={"currency": "EUR", "initial_balance": "0"})
        response = client.post(f"/users/{user['id']}/wallets/", json={"currency": "EUR", "initial_balance": "0"})
        assert response.status_code == 409

    def test_list_wallets(self, client):
        user = client.post("/users/", json={"username": "heidi", "email": "heidi@test.com"}).json()
        client.post(f"/users/{user['id']}/wallets/", json={"currency": "USD", "initial_balance": "0"})
        client.post(f"/users/{user['id']}/wallets/", json={"currency": "GBP", "initial_balance": "0"})
        response = client.get(f"/users/{user['id']}/wallets/")
        assert response.status_code == 200
        assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# Transfer & transaction endpoint tests
# ---------------------------------------------------------------------------

class TestTransferEndpoints:
    def test_successful_transfer(self, client, two_users_with_wallets):
        _, _, alice_wallet, bob_wallet = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "200",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert Decimal(data["amount"]) == Decimal("200")

    def test_transfer_updates_balances(self, client, two_users_with_wallets):
        alice, bob, alice_wallet, bob_wallet = two_users_with_wallets
        client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "150",
        })
        updated_alice = client.get(f"/users/{alice['id']}/wallets/{alice_wallet['id']}").json()
        updated_bob = client.get(f"/users/{bob['id']}/wallets/{bob_wallet['id']}").json()
        assert Decimal(updated_alice["balance"]) == Decimal("350")
        assert Decimal(updated_bob["balance"]) == Decimal("250")

    def test_transfer_insufficient_funds_returns_400(self, client, two_users_with_wallets):
        _, _, alice_wallet, bob_wallet = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "9999",
        })
        assert response.status_code == 400

    def test_transfer_to_same_wallet_returns_400(self, client, two_users_with_wallets):
        _, _, alice_wallet, _ = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": alice_wallet["id"],
            "amount": "10",
        })
        assert response.status_code == 400

    def test_get_wallet_transactions(self, client, two_users_with_wallets):
        alice, _, alice_wallet, bob_wallet = two_users_with_wallets
        client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "50",
        })
        response = client.get(f"/wallets/{alice_wallet['id']}/transactions")
        assert response.status_code == 200
        txns = response.json()
        assert len(txns) == 1
        assert Decimal(txns[0]["amount"]) == Decimal("50")

    def test_zero_amount_transfer_returns_422(self, client, two_users_with_wallets):
        _, _, alice_wallet, bob_wallet = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "0",
        })
        assert response.status_code == 422
