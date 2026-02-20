import enum


class Currency(str, enum.Enum):
    USD = "USD"   # US Dollar
    EUR = "EUR"   # Euro
    GBP = "GBP"   # British Pound
    BTC = "BTC"   # Bitcoin (cryptocurrency)
