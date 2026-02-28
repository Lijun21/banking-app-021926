import type { Currency } from "../api/wallets";

// Hard-coded rates mirrored from app/services/currency_service.py
// All rates are: 1 unit of currency = X USD
export const RATES_TO_USD: Record<Currency, number> = {
  USD: 1,
  EUR: 1.08,
  GBP: 1.27,
  BTC: 52000,
};

export interface Quote {
  sendAmount: number;
  receiveAmount: number;
  rate: number;
  fromCurrency: Currency;
  toCurrency: Currency;
}

export function getQuote(
  amount: number,
  from: Currency,
  to: Currency
): Quote {
  if (from === to) {
    return { sendAmount: amount, receiveAmount: amount, rate: 1, fromCurrency: from, toCurrency: to };
  }
  const inUSD = amount * RATES_TO_USD[from];
  const receiveAmount = inUSD / RATES_TO_USD[to];
  const rate = RATES_TO_USD[from] / RATES_TO_USD[to];
  return { sendAmount: amount, receiveAmount, rate, fromCurrency: from, toCurrency: to };
}
