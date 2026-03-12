import { useEffect, useState, useCallback, type FormEvent } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { listWallets, searchUserWallets, type WalletResponse, type Currency } from "../api/wallets";
import { transfer, type TransactionResponse } from "../api/transactions";
import { getQuote, type Quote } from "../utils/rates";
import { formatAmount, maskId } from "../utils/format";
import { ApiError } from "../api/client";

const CURRENCIES: Currency[] = ["USD", "EUR", "GBP", "BTC"];

type Step = "form" | "quote" | "result";

export default function TransferPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preselectedFrom = params.get("from") ?? "";

  const [wallets, setWallets] = useState<WalletResponse[]>([]);
  const [step, setStep] = useState<Step>("form");

  // Form state
  const [fromWalletId, setFromWalletId] = useState(preselectedFrom);
  const [toUsername, setToUsername] = useState("");
  const [toCurrency, setToCurrency] = useState<Currency>("USD");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState("");
  const [resolving, setResolving] = useState(false);

  // Resolved destination wallet (after lookup)
  const [toWallet, setToWallet] = useState<WalletResponse | null>(null);

  // Quote state
  const [quote, setQuote] = useState<Quote | null>(null);
  const [countdown, setCountdown] = useState(60);
  // Idempotency key — generated once per quote, reused on retries
  const [idempotencyKey, setIdempotencyKey] = useState("");

  // Result state
  const [result, setResult] = useState<TransactionResponse | null>(null);
  const [transferError, setTransferError] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);

  useEffect(() => {
    if (!user) { navigate("/login"); return; }
    listWallets(user.id).then(setWallets).catch(() => navigate("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Countdown timer on quote screen
  useEffect(() => {
    if (step !== "quote") return;
    setCountdown(60);
    const id = setInterval(() => {
      setCountdown((c) => (c <= 1 ? 60 : c - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [step, quote]);

  const fromWallet = wallets.find((w) => w.id === fromWalletId);

  async function handleGetQuote(e: FormEvent) {
    e.preventDefault();
    setFormError("");

    const numAmount = parseFloat(amount);
    if (!fromWallet) { setFormError("Select a source wallet."); return; }
    if (!toUsername.trim()) { setFormError("Enter a recipient username."); return; }
    if (isNaN(numAmount) || numAmount <= 0) {
      setFormError("Amount must be a positive number.");
      return;
    }
    if (numAmount > parseFloat(fromWallet.balance)) {
      setFormError(
        `Insufficient funds. Available: ${formatAmount(fromWallet.balance, fromWallet.currency)}`
      );
      return;
    }

    // Resolve username → wallet
    setResolving(true);
    try {
      const recipientWallets = await searchUserWallets(toUsername.trim());
      const matched = recipientWallets.find((w) => w.currency === toCurrency);
      if (!matched) {
        setFormError(`User "${toUsername}" has no ${toCurrency} wallet.`);
        return;
      }
      if (matched.id === fromWalletId) {
        setFormError("You can't send money to your own wallet.");
        return;
      }
      setToWallet(matched);
      const q = getQuote(numAmount, fromWallet.currency, toCurrency);
      setQuote(q);
      setIdempotencyKey(crypto.randomUUID()); // fresh key per quote
      setStep("quote");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setFormError(`User "${toUsername}" not found.`);
      } else {
        setFormError("Could not look up recipient. Try again.");
      }
    } finally {
      setResolving(false);
    }
  }

  const handleConfirm = useCallback(async () => {
    if (!fromWallet || !toWallet) return;
    setConfirmLoading(true);
    setTransferError("");
    try {
      const txn = await transfer(fromWalletId, toWallet.id, amount, note || undefined, idempotencyKey);
      setResult(txn);
      setStep("result");
      // Refresh wallet balances so "Send Another" shows updated amounts
      if (user) listWallets(user.id).then(setWallets).catch(() => {});
    } catch (err) {
      if (err instanceof ApiError) {
        setTransferError(err.detail);
      } else {
        setTransferError("Something went wrong. Please try again.");
      }
    } finally {
      setConfirmLoading(false);
    }
  }, [fromWalletId, toWallet, amount, note, fromWallet, user, idempotencyKey]);

  if (!user) return null;

  // ─── Step 1: Form ────────────────────────────────────────────────────────
  if (step === "form") {
    return (
      <div className="max-w-md mx-auto">
        <h1 className="text-xl font-bold text-gray-900 mb-6">Send Money</h1>

        <form onSubmit={handleGetQuote} className="bg-white rounded-2xl border border-gray-200 p-6 space-y-5 shadow-sm">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              From wallet
            </label>
            <select
              value={fromWalletId}
              onChange={(e) => setFromWalletId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a wallet…</option>
              {wallets.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.currency} — balance: {formatAmount(w.balance, w.currency)} ···{w.id.slice(-4)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Recipient username
            </label>
            <input
              type="text"
              value={toUsername}
              onChange={(e) => setToUsername(e.target.value)}
              placeholder="e.g. bob"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Send to their
            </label>
            <select
              value={toCurrency}
              onChange={(e) => setToCurrency(e.target.value as Currency)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>{c} wallet</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount
              {fromWallet && (
                <span className="text-gray-400 font-normal ml-1">
                  (in {fromWallet.currency})
                </span>
              )}
            </label>
            <input
              type="number"
              min="0.00000001"
              step="any"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Note <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. rent"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {formError && (
            <p className="text-red-500 text-sm">✗ {formError}</p>
          )}

          <button
            type="submit"
            disabled={resolving}
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {resolving ? "Looking up recipient…" : "Get Quote →"}
          </button>
        </form>

        <button
          onClick={() => navigate("/dashboard")}
          className="mt-4 text-sm text-gray-500 hover:text-gray-700"
        >
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  // ─── Step 2: Quote review ─────────────────────────────────────────────────
  if (step === "quote" && quote && fromWallet && toWallet) {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">Transfer Quote</h1>
            <span className="text-sm text-orange-500 font-medium bg-orange-50 px-3 py-1 rounded-full">
              ⏱ Rate locked {countdown}s
            </span>
          </div>

          <hr className="border-gray-100" />

          <div className="space-y-3">
            <Row label="You send" value={formatAmount(quote.sendAmount, fromWallet.currency)} />
            <Row
              label="Recipient gets (est.)"
              value={formatAmount(quote.receiveAmount, toWallet.currency)}
            />
            {fromWallet.currency !== toWallet.currency && (
              <Row
                label="Exchange rate"
                value={`1 ${fromWallet.currency} = ${quote.rate.toFixed(6)} ${toWallet.currency}`}
              />
            )}
            <Row label="To" value={`@${toUsername} (${toCurrency})`} />
            <Row label="From wallet" value={maskId(fromWalletId)} />
            <Row label="To wallet" value={maskId(toWallet.id)} />
            {note && <Row label="Note" value={note} />}
          </div>

          <hr className="border-gray-100" />

          {transferError && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-600">
              ✗ {transferError}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setStep("form")}
              className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50 transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={handleConfirm}
              disabled={confirmLoading}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {confirmLoading ? "Sending…" : "Confirm & Send"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Step 3: Result ────────────────────────────────────────────────────────
  if (step === "result" && result) {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm text-center space-y-5">
          <div className="text-5xl">✅</div>
          <h1 className="text-xl font-bold text-gray-900">Transfer Complete</h1>

          <div className="bg-gray-50 rounded-xl p-4 text-left space-y-2">
            <Row label="You sent" value={formatAmount(result.amount, result.currency)} />
            <Row label="To" value={`@${toUsername}`} />
            <Row label="Transaction ID" value={maskId(result.id)} />
            <Row label="Status" value={<span className="text-green-600 font-medium">{result.status}</span>} />
            {result.note && <Row label="Note" value={result.note} />}
          </div>

          <div className="flex gap-3">
            <Link
              to={`/wallets/${fromWalletId}/transactions`}
              className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50 transition-colors text-center"
            >
              View History
            </Link>
            <button
              onClick={() => {
                setStep("form");
                setAmount("");
                setToUsername("");
                setNote("");
                setResult(null);
                setToWallet(null);
              }}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Send Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{value}</span>
    </div>
  );
}
