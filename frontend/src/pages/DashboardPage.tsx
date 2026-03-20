import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { listWallets, type WalletResponse } from "../api/wallets";
import { getWalletTransactions, type TransactionResponse } from "../api/transactions";
import { ApiError } from "../api/client";
import WalletCard from "../components/WalletCard";
import AddWalletModal from "../components/AddWalletModal";
import { formatAmount, formatDate } from "../utils/format";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [wallets, setWallets] = useState<WalletResponse[]>([]);
  const [recentTxns, setRecentTxns] = useState<TransactionResponse[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!user) navigate("/login", { state: { message: "Please log in." } });
  }, [user, navigate]);

  async function fetchWallets() {
    if (!user) return;
    setError("");
    try {
      const ws = await listWallets(user.id);
      setWallets(ws);

      // Fetch recent transactions across all wallets (first page, 5 per wallet)
      const txnArrays = await Promise.all(
        ws.map((w) => getWalletTransactions(w.id, undefined, 5))
      );
      const all = txnArrays
        .flatMap((r) => r.items)
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 6);
      setRecentTxns(all);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login", { state: { message: "Session expired — log in again." } });
      } else {
        setError("Failed to load wallets.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchWallets();
    // Re-fetch whenever the user navigates to this page (location.key changes on each navigation)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, location.key]);

  if (!user) return null;

  return (
    <div className="space-y-8">
      {/* Wallets section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">My Wallets</h2>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            + Add Wallet
          </button>
        </div>

        {loading && (
          <p className="text-sm text-gray-400">Loading wallets…</p>
        )}
        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}

        {!loading && wallets.length === 0 && !error && (
          <div className="bg-white rounded-xl border border-dashed border-gray-200 p-10 text-center text-gray-400 text-sm">
            No wallets yet.{" "}
            <button
              onClick={() => setShowAddModal(true)}
              className="text-blue-600 hover:underline"
            >
              Add your first wallet
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {wallets.map((w) => (
            <WalletCard key={w.id} wallet={w} userId={user.id} />
          ))}
        </div>
      </section>

      {/* Recent activity */}
      {recentTxns.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Activity
          </h2>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {recentTxns.map((txn) => {
              const isSent = wallets.some((w) => w.id === txn.from_wallet_id);
              return (
                <div key={txn.id} className="flex items-center justify-between px-5 py-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-sm font-medium ${isSent ? "text-red-500" : "text-green-500"}`}
                    >
                      {isSent ? "▼ Sent" : "▲ Received"}
                    </span>
                    <span className="text-sm text-gray-700">
                      {formatAmount(txn.amount, txn.currency)}{" "}
                      <span className="text-gray-400 text-xs">
                        {formatDate(txn.created_at)}
                      </span>
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
              );
            })}
          </div>
        </section>
      )}

      {showAddModal && (
        <AddWalletModal
          userId={user.id}
          onCreated={() => {
            setShowAddModal(false);
            fetchWallets();
          }}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
}
