"""
Hard-coded exchange rates relative to USD.
In a real system these would come from a live API (e.g. CoinGecko, Open Exchange Rates).
"""
from decimal import Decimal
from app.models.currency import Currency

# Rates: 1 unit of currency = X USD
RATES_TO_USD: dict[Currency, Decimal] = {
    Currency.USD: Decimal("1"),
    Currency.EUR: Decimal("1.08"),
    Currency.GBP: Decimal("1.27"),
    Currency.BTC: Decimal("52000"),  # approximate; hard-coded for this demo
}


def convert(amount: Decimal, from_currency: Currency, to_currency: Currency) -> Decimal:
    """Convert an amount from one currency to another via USD as the pivot."""
    if from_currency == to_currency:
        return amount
    in_usd = amount * RATES_TO_USD[from_currency]
    converted = in_usd / RATES_TO_USD[to_currency]
    # Round to 8 decimal places (handles crypto precision)
    return converted.quantize(Decimal("0.00000001"))
