import { api } from "./client";

export type Currency = "USD" | "EUR" | "GBP" | "BTC";

export interface WalletResponse {
  id: string;
  owner_id: string;
  currency: Currency;
  balance: string;
  created_at: string;
}

export function listWallets(userId: string): Promise<WalletResponse[]> {
  return api.get(`/users/${userId}/wallets/`);
}

export function getWallet(
  userId: string,
  walletId: string
): Promise<WalletResponse> {
  return api.get(`/users/${userId}/wallets/${walletId}`);
}

export function createWallet(
  userId: string,
  currency: Currency,
  initialBalance?: string
): Promise<WalletResponse> {
  return api.post(`/users/${userId}/wallets/`, {
    currency,
    initial_balance: initialBalance ?? "0",
  });
}

export function searchUserWallets(username: string): Promise<WalletResponse[]> {
  return api.get(`/users/search?username=${encodeURIComponent(username)}`);
}
