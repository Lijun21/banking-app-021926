import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getWalletTransactions, type TransactionResponse } from "../api/transactions";
import { listWallets, type WalletResponse } from "../api/wallets";
import { ApiError } from "../api/client";
import { formatAmount, formatDate, maskId } from "../utils/format";

const PAGE_SIZE = 20;

export default function TransactionHistoryPage() {
  const { walletId } = useParams<{ walletId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [transactions, setTransactions] = useState<TransactionResponse[]>([]);
  const [wallet, setWallet] = useState<WalletResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!user) { navigate("/login"); return; }
    if (!walletId) { navigate("/dashboard"); return; }

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [result, wallets] = await Promise.all([
          getWalletTransactions(walletId!, page, PAGE_SIZE),
          listWallets(user!.id),
        ]);
        setTransactions(result.items);
        setTotalPages(result.pages);
        setTotal(result.total);
        const found = wallets.find((w) => w.id === walletId);
        setWallet(found ?? null);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { state: { message: "Session expired — log in again." } });
        } else {
          setError("Failed to load transactions.");
        }
      } finally {
        setLoading(false);
      }
    }

    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId, page, user]);

  const filtered = transactions.filter((t) => {
    if (!search) return true;
    return t.note?.toLowerCase().includes(search.toLowerCase());
  });

  // Reset to page 1 when search changes
  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  if (!user) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {wallet
              ? `${wallet.currency} Wallet ${maskId(walletId!)}`
              : "Wallet"}{" "}
            — Transaction History
          </h1>
          {wallet && (
            <p className="text-sm text-gray-500 mt-1">
              Balance: {formatAmount(wallet.balance, wallet.currency)}
            </p>
          )}
        </div>
        <button
          onClick={() => navigate("/dashboard")}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Back
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search by note…"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 flex-1"
        />
      </div>

      {loading && (
        <p className="text-sm text-gray-400">Loading…</p>
      )}
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {!loading && filtered.length === 0 && !error && (
        <div className="bg-white rounded-xl border border-dashed border-gray-200 p-10 text-center text-gray-400 text-sm">
          No transactions found.
        </div>
      )}

      {filtered.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 shadow-sm">
          {filtered.map((txn) => {
            const isSent = txn.from_wallet_id === walletId;
            return (
              <div key={txn.id} className="px-5 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-sm font-semibold ${
                        isSent ? "text-red-500" : "text-green-500"
                      }`}
                    >
                      {isSent ? "▼ SENT" : "▲ RECEIVED"}
                    </span>
                    <span className="text-xs text-gray-400">
                      {formatDate(txn.created_at)}
                    </span>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      txn.status === "completed"
                        ? "bg-green-50 text-green-600"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {txn.status}
                  </span>
                </div>

                <div className="mt-2 text-sm text-gray-700">
                  <span className="font-medium">
                    {formatAmount(txn.amount, txn.currency)}
                  </span>{" "}
                  {isSent ? (
                    <>
                      → <span className="font-mono text-gray-500">{maskId(txn.to_wallet_id)}</span>
                    </>
                  ) : (
                    <>
                      ← <span className="font-mono text-gray-500">{maskId(txn.from_wallet_id)}</span>
                    </>
                  )}
                </div>

                {txn.note && (
                  <p className="text-xs text-gray-400 mt-1">Note: {txn.note}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-xs text-gray-400">
            {total} transaction{total !== 1 ? "s" : ""} — page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page === 1}
              className="px-2 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              «
            </button>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              Prev
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
              .reduce<(number | "…")[]>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push("…");
                acc.push(p);
                return acc;
              }, [])
              .map((item, idx) =>
                item === "…" ? (
                  <span key={`ellipsis-${idx}`} className="px-2 text-gray-400 text-sm">…</span>
                ) : (
                  <button
                    key={item}
                    onClick={() => setPage(item as number)}
                    className={`px-3 py-1 text-sm rounded border ${
                      page === item
                        ? "bg-blue-600 text-white border-blue-600"
                        : "border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {item}
                  </button>
                ),
              )}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page === totalPages}
              className="px-2 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              »
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
