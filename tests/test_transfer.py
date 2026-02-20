import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.models.wallet import Wallet
from app.models.currency import Currency
from app.services.transfer_service import transfer
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

def _make_wallet(wallet_id: str, currency: Currency, balance: Decimal) -> Wallet:
    w = MagicMock(spec=Wallet)
    w.id = wallet_id
    w.currency = currency
    w.balance = balance
    return w


class TestTransferService:
    def _db(self, from_wallet, to_wallet):
        db = MagicMock()
        db.get.side_effect = lambda model, wid: (
            from_wallet if wid == from_wallet.id else to_wallet
        )
        return db

    def test_same_wallet_raises_400(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            transfer(db, "w1", "w1", Decimal("10"))
        assert exc_info.value.status_code == 400

    def test_source_wallet_not_found_raises_404(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            transfer(db, "nonexistent", "w2", Decimal("10"))
        assert exc_info.value.status_code == 404

    def test_insufficient_funds_raises_400(self):
        from_w = _make_wallet("w1", Currency.USD, Decimal("5"))
        to_w = _make_wallet("w2", Currency.USD, Decimal("0"))
        db = self._db(from_w, to_w)
        with pytest.raises(HTTPException) as exc_info:
            transfer(db, "w1", "w2", Decimal("10"))
        assert exc_info.value.status_code == 400

    def test_same_currency_transfer_debits_and_credits(self):
        from_w = _make_wallet("w1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", Currency.USD, Decimal("50"))
        db = self._db(from_w, to_w)

        transfer(db, "w1", "w2", Decimal("30"))

        assert from_w.balance == Decimal("70")
        assert to_w.balance == Decimal("80")
        db.commit.assert_called_once()

    def test_cross_currency_transfer_converts_amount(self):
        from_w = _make_wallet("w1", Currency.USD, Decimal("1000"))
        to_w = _make_wallet("w2", Currency.EUR, Decimal("0"))
        db = self._db(from_w, to_w)

        transfer(db, "w1", "w2", Decimal("108"))

        assert from_w.balance == Decimal("892")
        # 108 USD → 100 EUR (rate 1.08)
        assert to_w.balance == Decimal("100.00000000")

    def test_transaction_record_is_saved(self):
        from_w = _make_wallet("w1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", Currency.USD, Decimal("0"))
        db = self._db(from_w, to_w)

        transfer(db, "w1", "w2", Decimal("50"), note="rent")

        db.add.assert_called_once()
        added_txn = db.add.call_args[0][0]
        assert added_txn.amount == Decimal("50")
        assert added_txn.note == "rent"
        assert added_txn.status == "completed"

    def test_wallets_are_locked_with_select_for_update(self):
        """
        Verify that with_for_update() is called on the query so that
        PostgreSQL acquires a row-level lock during transfers.
        (SQLite silently ignores FOR UPDATE, but we at least assert intent.)
        """
        from_w = _make_wallet("w1", Currency.USD, Decimal("100"))
        to_w = _make_wallet("w2", Currency.USD, Decimal("0"))

        # Build a mock query chain: db.query().filter().with_for_update().all()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_for_update = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_for_update
        mock_for_update.all.return_value = [from_w, to_w]

        db = MagicMock()
        db.query.return_value = mock_query

        transfer(db, "w1", "w2", Decimal("50"))

        mock_filter.with_for_update.assert_called_once()  # lock was requested ✅
