import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.models.wallet import Wallet
from app.models.currency import Currency
from app.models.transaction import Transaction, TransferStatus
from app.services.transfer_service import lock_quote, confirm_transfer
from app.services.currency_service import convert


# ---------------------------------------------------------------------------
# currency_service tests
# ---------------------------------------------------------------------------

class TestCurrencyConversion:
    def test_same_currency_returns_same_amount(self):
        result = convert(Decimal("100"), Currency.USD, Currency.USD)
        assert result == Decimal("100")

    def test_usd_to_eur(self):
        # 100 USD / 1.08 EUR_rate = ~92.59 EUR
        result = convert(Decimal("100"), Currency.USD, Currency.EUR)
        assert result == Decimal("92.59259259")

    def test_usd_to_btc(self):
        # 52000 USD = 1 BTC → 1000 USD = 1000/52000 BTC
        result = convert(Decimal("1000"), Currency.USD, Currency.BTC)
        assert result == Decimal("0.01923077")

    def test_btc_to_usd(self):
        # 1 BTC = 52000 USD
        result = convert(Decimal("1"), Currency.BTC, Currency.USD)
        assert result == Decimal("52000.00000000")

    def test_eur_to_gbp(self):
        # 100 EUR → 108 USD → 108/1.27 GBP
        result = convert(Decimal("100"), Currency.EUR, Currency.GBP)
        assert result > Decimal("0")


# ---------------------------------------------------------------------------
# transfer_service tests (using mocked DB session)
# ---------------------------------------------------------------------------

def _make_wallet(wallet_id: str, owner_id: str, currency: Currency, balance: Decimal) -> Wallet:
    w = MagicMock(spec=Wallet)
    w.id = wallet_id
    w.owner_id = owner_id
    w.currency = currency
    w.balance = balance
    return w


def _db_for_lock_quote(from_wallet, to_wallet):
    """Mock DB for lock_quote: db.get() returns wallets by id."""
    db = MagicMock()
    db.get.side_effect = lambda model, wid: {from_wallet.id: from_wallet, to_wallet.id: to_wallet}.get(wid)
    return db


def _db_for_confirm(txn, from_wallet, to_wallet):
    """Mock DB for confirm_transfer: query chain returns txn, db.get returns from_wallet."""
    db = MagicMock()
    # db.query(Transaction).filter(...).with_for_update().first() → txn
    mock_txn_chain = MagicMock()
    mock_txn_chain.filter.return_value.with_for_update.return_value.first.return_value = txn
    # db.query(Wallet).filter(...).with_for_update().all() → wallets
    mock_wallet_chain = MagicMock()
    mock_wallet_chain.filter.return_value.with_for_update.return_value.all.return_value = sorted(
        [from_wallet, to_wallet], key=lambda w: w.id
    )
    db.query.side_effect = lambda model: mock_txn_chain if model is Transaction else mock_wallet_chain
    db.get.return_value = from_wallet
    return db


class TestLockQuoteService:
    def test_same_wallet_raises_400(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            lock_quote(db, "w1", "w1", Decimal("10"), requester_id="user1")
        assert exc_info.value.status_code == 400

    def test_source_wallet_not_found_raises_404(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            lock_quote(db, "nonexistent", "w2", Decimal("10"), requester_id="user1")
        assert exc_info.value.status_code == 404

    def test_ownership_check_raises_403(self):
        from_w = _make_wallet("w1", "alice", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "bob", Currency.USD, Decimal("0"))
        db = _db_for_lock_quote(from_w, to_w)
        with pytest.raises(HTTPException) as exc_info:
            lock_quote(db, "w1", "w2", Decimal("50"), requester_id="bob")
        assert exc_info.value.status_code == 403

    def test_insufficient_funds_raises_400(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("5"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("0"))
        db = _db_for_lock_quote(from_w, to_w)
        with pytest.raises(HTTPException) as exc_info:
            lock_quote(db, "w1", "w2", Decimal("10"), requester_id="user1")
        assert exc_info.value.status_code == 400

    def test_creates_quote_locked_transaction(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("0"))
        db = _db_for_lock_quote(from_w, to_w)

        lock_quote(db, "w1", "w2", Decimal("50"), requester_id="user1", note="rent")

        db.add.assert_called_once()
        added_txn = db.add.call_args[0][0]
        assert added_txn.amount == Decimal("50")
        assert added_txn.note == "rent"
        assert added_txn.status == TransferStatus.QUOTE_LOCKED

    def test_same_currency_locks_rate_1(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("0"))
        db = _db_for_lock_quote(from_w, to_w)

        lock_quote(db, "w1", "w2", Decimal("50"), requester_id="user1")

        added_txn = db.add.call_args[0][0]
        assert added_txn.rate == Decimal("1")
        assert added_txn.receive_amount == Decimal("50")

    def test_cross_currency_locks_converted_rate(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("1000"))
        to_w = _make_wallet("w2", "user2", Currency.EUR, Decimal("0"))
        db = _db_for_lock_quote(from_w, to_w)

        lock_quote(db, "w1", "w2", Decimal("108"), requester_id="user1")

        added_txn = db.add.call_args[0][0]
        assert added_txn.receive_amount == Decimal("100.00000000")


class TestConfirmTransferService:
    def _make_txn(self, from_wallet_id, to_wallet_id, amount, receive_amount, status=TransferStatus.QUOTE_LOCKED):
        from datetime import datetime, timezone, timedelta
        txn = MagicMock(spec=Transaction)
        txn.id = "txn1"
        txn.from_wallet_id = from_wallet_id
        txn.to_wallet_id = to_wallet_id
        txn.amount = amount
        txn.receive_amount = receive_amount
        txn.status = status
        txn.expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        return txn

    def test_transfer_not_found_raises_404(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            confirm_transfer(db, "bad_id", "user1")
        assert exc_info.value.status_code == 404

    def test_already_completed_returns_idempotently(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("0"))
        txn = self._make_txn("w1", "w2", Decimal("50"), Decimal("50"), status=TransferStatus.COMPLETED)
        db = _db_for_confirm(txn, from_w, to_w)

        result = confirm_transfer(db, "txn1", "user1")
        assert result is txn  # returned as-is, no double execution

    def test_expired_quote_raises_410(self):
        from datetime import datetime, timezone, timedelta
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("0"))
        txn = self._make_txn("w1", "w2", Decimal("50"), Decimal("50"))
        txn.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)  # already expired
        db = _db_for_confirm(txn, from_w, to_w)

        with pytest.raises(HTTPException) as exc_info:
            confirm_transfer(db, "txn1", "user1")
        assert exc_info.value.status_code == 410
        assert txn.status == TransferStatus.EXPIRED

    def test_confirm_debits_and_credits_balances(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("50"))
        txn = self._make_txn("w1", "w2", Decimal("30"), Decimal("30"))
        db = _db_for_confirm(txn, from_w, to_w)

        confirm_transfer(db, "txn1", "user1")

        assert from_w.balance == Decimal("70")
        assert to_w.balance == Decimal("80")
        assert txn.status == TransferStatus.COMPLETED

    def test_confirm_uses_locked_rate_for_cross_currency(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("1000"))
        to_w = _make_wallet("w2", "user2", Currency.EUR, Decimal("0"))
        txn = self._make_txn("w1", "w2", Decimal("108"), Decimal("100.00000000"))
        db = _db_for_confirm(txn, from_w, to_w)

        confirm_transfer(db, "txn1", "user1")

        assert from_w.balance == Decimal("892")
        assert to_w.balance == Decimal("100.00000000")  # uses locked receive_amount, not recalculated

    def test_wallets_are_locked_with_select_for_update(self):
        from_w = _make_wallet("w1", "user1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", "user2", Currency.USD, Decimal("0"))
        txn = self._make_txn("w1", "w2", Decimal("50"), Decimal("50"))

        # Build mock manually to keep a handle on the wallet query chain
        db = MagicMock()
        mock_txn_chain = MagicMock()
        mock_txn_chain.filter.return_value.with_for_update.return_value.first.return_value = txn
        mock_wallet_chain = MagicMock()
        mock_wallet_chain.filter.return_value.with_for_update.return_value.all.return_value = sorted(
            [from_w, to_w], key=lambda w: w.id
        )
        db.query.side_effect = lambda model: mock_txn_chain if model is Transaction else mock_wallet_chain
        db.get.return_value = from_w

        confirm_transfer(db, "txn1", "user1")

        # Verify SELECT FOR UPDATE was requested for wallet locking
        mock_wallet_chain.filter.return_value.with_for_update.assert_called_once()
