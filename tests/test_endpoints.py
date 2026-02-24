"""
Integration-style tests for the banking app endpoints.
Uses a real PostgreSQL test database (see tests/conftest.py).

Start the test DB before running:
    docker compose up db_test -d
"""
import pytest
from decimal import Decimal


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def register_and_login(client, username: str, email: str, password: str = "testpass123"):
    """Register a user with a password and return (user_data, auth_headers)."""
    user = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    ).json()
    token = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture
def two_users_with_wallets(client):
    """Create two users each with a USD wallet and seed balances."""
    alice, alice_headers = register_and_login(client, "alice", "alice@example.com")
    bob, bob_headers = register_and_login(client, "bob", "bob@example.com")

    alice_wallet = client.post(
        f"/users/{alice['id']}/wallets/",
        json={"currency": "USD", "initial_balance": "500"},
        headers=alice_headers,
    ).json()
    bob_wallet = client.post(
        f"/users/{bob['id']}/wallets/",
        json={"currency": "USD", "initial_balance": "100"},
        headers=bob_headers,
    ).json()

    return alice, bob, alice_wallet, bob_wallet, alice_headers, bob_headers


# ---------------------------------------------------------------------------
# Auth endpoint tests
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    def test_register_creates_user(self, client):
        response = client.post(
            "/auth/register",
            json={"username": "newuser", "email": "new@test.com", "password": "secret"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data

    def test_register_duplicate_returns_409(self, client):
        client.post("/auth/register", json={"username": "dup", "email": "dup@test.com", "password": "x"})
        response = client.post("/auth/register", json={"username": "dup", "email": "dup@test.com", "password": "x"})
        assert response.status_code == 409

    def test_login_returns_token(self, client):
        client.post("/auth/register", json={"username": "u", "email": "u@test.com", "password": "pass"})
        response = client.post("/auth/token", data={"username": "u", "password": "pass"})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password_returns_401(self, client):
        client.post("/auth/register", json={"username": "u2", "email": "u2@test.com", "password": "correct"})
        response = client.post("/auth/token", data={"username": "u2", "password": "wrong"})
        assert response.status_code == 401

    def test_login_unknown_user_returns_401(self, client):
        response = client.post("/auth/token", data={"username": "ghost", "password": "x"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# User endpoint tests
# ---------------------------------------------------------------------------

class TestUserEndpoints:
    def test_create_user(self, client):
        user, _ = register_and_login(client, "carol", "carol@test.com")
        assert user["username"] == "carol"
        assert "id" in user

    def test_duplicate_user_returns_409(self, client):
        client.post("/auth/register", json={"username": "dave", "email": "dave@test.com", "password": "x"})
        response = client.post("/auth/register", json={"username": "dave", "email": "dave@test.com", "password": "x"})
        assert response.status_code == 409

    def test_get_user(self, client):
        user, _ = register_and_login(client, "eve", "eve@test.com")
        response = client.get(f"/users/{user['id']}")
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
        user, headers = register_and_login(client, "frank", "frank@test.com")
        response = client.post(
            f"/users/{user['id']}/wallets/",
            json={"currency": "BTC", "initial_balance": "0.5"},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "BTC"
        assert Decimal(data["balance"]) == Decimal("0.5")

    def test_create_wallet_without_auth_returns_401(self, client):
        user, _ = register_and_login(client, "noauth", "noauth@test.com")
        response = client.post(
            f"/users/{user['id']}/wallets/",
            json={"currency": "USD", "initial_balance": "0"},
            # no headers — intentionally unauthenticated
        )
        assert response.status_code == 401

    def test_create_wallet_for_other_user_returns_403(self, client):
        user_a, headers_a = register_and_login(client, "usera", "usera@test.com")
        user_b, _ = register_and_login(client, "userb", "userb@test.com")
        # user_a tries to create a wallet under user_b's account
        response = client.post(
            f"/users/{user_b['id']}/wallets/",
            json={"currency": "USD", "initial_balance": "0"},
            headers=headers_a,
        )
        assert response.status_code == 403

    def test_duplicate_currency_wallet_returns_409(self, client):
        user, headers = register_and_login(client, "grace", "grace@test.com")
        client.post(f"/users/{user['id']}/wallets/", json={"currency": "EUR", "initial_balance": "0"}, headers=headers)
        response = client.post(f"/users/{user['id']}/wallets/", json={"currency": "EUR", "initial_balance": "0"}, headers=headers)
        assert response.status_code == 409

    def test_list_wallets(self, client):
        user, headers = register_and_login(client, "heidi", "heidi@test.com")
        client.post(f"/users/{user['id']}/wallets/", json={"currency": "USD", "initial_balance": "0"}, headers=headers)
        client.post(f"/users/{user['id']}/wallets/", json={"currency": "GBP", "initial_balance": "0"}, headers=headers)
        response = client.get(f"/users/{user['id']}/wallets/", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_wallets_without_auth_returns_401(self, client):
        user, _ = register_and_login(client, "nolist", "nolist@test.com")
        response = client.get(f"/users/{user['id']}/wallets/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Transfer & transaction endpoint tests
# ---------------------------------------------------------------------------

class TestTransferEndpoints:
    def test_successful_transfer(self, client, two_users_with_wallets):
        _, _, alice_wallet, bob_wallet, alice_headers, _ = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "200",
        }, headers=alice_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert Decimal(data["amount"]) == Decimal("200")

    def test_transfer_updates_balances(self, client, two_users_with_wallets):
        alice, bob, alice_wallet, bob_wallet, alice_headers, bob_headers = two_users_with_wallets
        client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "150",
        }, headers=alice_headers)
        updated_alice = client.get(f"/users/{alice['id']}/wallets/{alice_wallet['id']}", headers=alice_headers).json()
        updated_bob = client.get(f"/users/{bob['id']}/wallets/{bob_wallet['id']}", headers=bob_headers).json()
        assert Decimal(updated_alice["balance"]) == Decimal("350")
        assert Decimal(updated_bob["balance"]) == Decimal("250")

    def test_transfer_insufficient_funds_returns_400(self, client, two_users_with_wallets):
        _, _, alice_wallet, bob_wallet, alice_headers, _ = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "9999",
        }, headers=alice_headers)
        assert response.status_code == 400

    def test_transfer_to_same_wallet_returns_400(self, client, two_users_with_wallets):
        _, _, alice_wallet, _, alice_headers, _ = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": alice_wallet["id"],
            "amount": "10",
        }, headers=alice_headers)
        assert response.status_code == 400

    def test_transfer_without_auth_returns_401(self, client, two_users_with_wallets):
        """Unauthenticated transfer request is rejected."""
        _, _, alice_wallet, bob_wallet, _, _ = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "10",
        })
        assert response.status_code == 401

    def test_transfer_from_other_users_wallet_returns_403(self, client, two_users_with_wallets):
        """Bob cannot initiate a transfer from Alice's wallet."""
        _, _, alice_wallet, bob_wallet, _, bob_headers = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "10",
        }, headers=bob_headers)
        assert response.status_code == 403

    def test_get_wallet_transactions(self, client, two_users_with_wallets):
        alice, _, alice_wallet, bob_wallet, alice_headers, _ = two_users_with_wallets
        client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "50",
        }, headers=alice_headers)
        response = client.get(f"/wallets/{alice_wallet['id']}/transactions", headers=alice_headers)
        assert response.status_code == 200
        txns = response.json()
        assert len(txns) == 1
        assert Decimal(txns[0]["amount"]) == Decimal("50")

    def test_get_transactions_without_auth_returns_401(self, client, two_users_with_wallets):
        _, _, alice_wallet, _, _, _ = two_users_with_wallets
        response = client.get(f"/wallets/{alice_wallet['id']}/transactions")
        assert response.status_code == 401

    def test_zero_amount_transfer_returns_422(self, client, two_users_with_wallets):
        _, _, alice_wallet, bob_wallet, alice_headers, _ = two_users_with_wallets
        response = client.post("/transfers", json={
            "from_wallet_id": alice_wallet["id"],
            "to_wallet_id": bob_wallet["id"],
            "amount": "0",
        }, headers=alice_headers)
        assert response.status_code == 422
