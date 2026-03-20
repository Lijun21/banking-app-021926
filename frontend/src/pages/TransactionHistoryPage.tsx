import { useEffect, useRef, useState, useCallback } from "react";
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
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  // Sentinel div at the bottom — observed to trigger next page load
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  // Guard against duplicate fetches when observer fires multiple times
  const isFetchingRef = useRef(false);

  // Load initial page + wallet info
  useEffect(() => {
    if (!user) { navigate("/login"); return; }
    if (!walletId) { navigate("/dashboard"); return; }

    async function loadInitial() {
      setLoadingInitial(true);
      setError("");
      setTransactions([]);
      setNextCursor(null);
      setHasMore(false);
      try {
        const [result, wallets] = await Promise.all([
          getWalletTransactions(walletId!, undefined, PAGE_SIZE),
          listWallets(user!.id),
        ]);
        setTransactions(result.items);
        setNextCursor(result.next_cursor);
        setHasMore(result.has_more);
        setWallet(wallets.find((w) => w.id === walletId) ?? null);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { state: { message: "Session expired — log in again." } });
        } else {
          setError("Failed to load transactions.");
        }
      } finally {
        setLoadingInitial(false);
      }
    }

    loadInitial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletId, user]);

  // Append the next page when called
  const loadMore = useCallback(async () => {
    if (isFetchingRef.current || !hasMore || !nextCursor || !walletId) return;
    isFetchingRef.current = true;
    setLoadingMore(true);
    try {
      const result = await getWalletTransactions(walletId, nextCursor, PAGE_SIZE);
      setTransactions((prev) => [...prev, ...result.items]);
      setNextCursor(result.next_cursor);
      setHasMore(result.has_more);
    } catch {
      // silently ignore; user can scroll again to retry
    } finally {
      setLoadingMore(false);
      isFetchingRef.current = false;
    }
  }, [hasMore, nextCursor, walletId]);

  // IntersectionObserver watches the sentinel div
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore(); },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  const filtered = transactions.filter((t) => {
    if (!search) return true;
    return t.note?.toLowerCase().includes(search.toLowerCase());
  });

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

      {/* Search */}
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by note…"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 flex-1"
        />
      </div>

      {loadingInitial && <p className="text-sm text-gray-400">Loading…</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {!loadingInitial && filtered.length === 0 && !error && (
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
                    <>→ <span className="font-mono text-gray-500">{maskId(txn.to_wallet_id)}</span></>
                  ) : (
                    <>← <span className="font-mono text-gray-500">{maskId(txn.from_wallet_id)}</span></>
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

      {/* Sentinel — entering viewport triggers loadMore via IntersectionObserver */}
      <div ref={sentinelRef} className="h-1" />

      {loadingMore && (
        <p className="text-center text-sm text-gray-400 mt-4">Loading more…</p>
      )}
      {!loadingInitial && !hasMore && transactions.length > 0 && (
        <p className="text-center text-xs text-gray-300 mt-4">All transactions loaded</p>
      )}
    </div>
  );
}
