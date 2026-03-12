import { api } from "./client";
import type { Currency } from "./wallets";

export interface TransactionResponse {
  id: string;
  from_wallet_id: string;
  to_wallet_id: string;
  amount: string;
  currency: Currency;
  status: string;
  note: string | null;
  created_at: string;
}

export function transfer(
  fromWalletId: string,
  toWalletId: string,
  amount: string,
  note?: string,
  idempotencyKey?: string
): Promise<TransactionResponse> {
  const extraHeaders = idempotencyKey
    ? { "Idempotency-Key": idempotencyKey }
    : undefined;
  return api.post(
    "/transfers",
    { from_wallet_id: fromWalletId, to_wallet_id: toWalletId, amount, note: note || undefined },
    extraHeaders
  );
}

export function getWalletTransactions(
  walletId: string,
  limit = 50
): Promise<TransactionResponse[]> {
  return api.get(`/wallets/${walletId}/transactions?limit=${limit}`);
}
