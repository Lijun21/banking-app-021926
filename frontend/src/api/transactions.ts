import { api } from "./client";
import type { Currency } from "./wallets";

export interface TransactionResponse {
  id: string;
  from_wallet_id: string;
  to_wallet_id: string;
  amount: string;
  currency: Currency;
  rate: string | null;
  receive_amount: string | null;
  status: string;
  note: string | null;
  created_at: string;
  expires_at: string;
  completed_at: string | null;
}

export function createTransfer(
  fromWalletId: string,
  toWalletId: string,
  amount: string,
  note?: string,
): Promise<TransactionResponse> {
  return api.post("/transfers", {
    from_wallet_id: fromWalletId,
    to_wallet_id: toWalletId,
    amount,
    note: note || undefined,
  });
}

export function confirmTransfer(transferId: string): Promise<TransactionResponse> {
  return api.post(`/transfers/${transferId}/confirm`, {});
}

export interface CursorPage {
  items: TransactionResponse[];
  next_cursor: string | null;
  has_more: boolean;
}

export function getWalletTransactions(
  walletId: string,
  cursor?: string,
  pageSize = 20,
): Promise<CursorPage> {
  const params = new URLSearchParams({ page_size: String(pageSize) });
  if (cursor) params.set("cursor", cursor);
  return api.get(`/wallets/${walletId}/transactions?${params}`);
}

