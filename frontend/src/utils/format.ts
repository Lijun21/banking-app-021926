import type { Currency } from "../api/wallets";

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  BTC: "₿",
};

const CURRENCY_DECIMALS: Record<Currency, number> = {
  USD: 2,
  EUR: 2,
  GBP: 2,
  BTC: 8,
};

export function formatAmount(amount: string | number, currency: Currency): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  const decimals = CURRENCY_DECIMALS[currency];
  const symbol = CURRENCY_SYMBOLS[currency];
  if (currency === "BTC") {
    return `${num.toFixed(decimals)} BTC`;
  }
  return `${symbol}${num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

export function currencyIcon(currency: Currency): string {
  return CURRENCY_SYMBOLS[currency];
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function maskId(id: string): string {
  return `···${id.slice(-4)}`;
}
