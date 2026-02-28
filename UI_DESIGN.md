# Banking App — UI Design

## Overview

A web UI (React or similar SPA) that wraps the existing FastAPI backend.  
Four primary flows:

1. **Register / Login** — create account, obtain JWT
2. **Dashboard** — wallet balances at a glance
3. **Transfer** — pick wallets → get a rate quote → confirm → done
4. **Transaction History** — paginated list per wallet

---

## User Journey Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  New User                                                           │
│  Register ──► Login ──► Dashboard ──► Create Wallet ──► Transfer   │
│                                 │                          │        │
│                                 └────► Transactions ◄──────┘        │
└─────────────────────────────────────────────────────────────────────┘

  Returning User
  Login ──► Dashboard
```

---

## Screen Designs

### 1. Register Screen

```
┌──────────────────────────────────────────┐
│          🏦  BankApp                     │
│                                          │
│   Create your account                   │
│                                          │
│   Username  ┌────────────────────────┐  │
│             │ alice                  │  │
│             └────────────────────────┘  │
│                                          │
│   Email     ┌────────────────────────┐  │
│             │ alice@example.com      │  │
│             └────────────────────────┘  │
│                                          │
│   Password  ┌────────────────────────┐  │
│             │ ••••••••               │  │
│             └────────────────────────┘  │
│                                          │
│             ┌────────────────────────┐  │
│             │    Create Account      │  │  ← POST /auth/register
│             └────────────────────────┘  │
│                                          │
│   Already have an account?  Log in      │
└──────────────────────────────────────────┘

Validation:
  • Username  — required, no spaces
  • Email     — valid format (pydantic EmailStr mirrors this)
  • Password  — min 8 chars shown client-side
  • 409 from server → "Username or email already taken"
```

---

### 2. Login Screen

```
┌──────────────────────────────────────────┐
│          🏦  BankApp                     │
│                                          │
│   Welcome back                          │
│                                          │
│   Username  ┌────────────────────────┐  │
│             │                        │  │
│             └────────────────────────┘  │
│                                          │
│   Password  ┌────────────────────────┐  │
│             │                        │  │
│             └────────────────────────┘  │
│                                          │
│             ┌────────────────────────┐  │
│             │        Log In          │  │  ← POST /auth/token
│             └────────────────────────┘  │
│                                          │
│   ✗ Incorrect username or password      │  ← 401 inline error
│                                          │
│   Don't have an account?  Register      │
└──────────────────────────────────────────┘

On success:
  • Store JWT in memory (not localStorage — XSS risk)
  • Redirect → Dashboard
```

---

### 3. Dashboard

```
┌────────────────────────────────────────────────────────────────────┐
│  🏦 BankApp          alice                  [Log Out]              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  My Wallets                                  [+ Add Wallet]        │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐   │
│  │  💵 USD          │  │  ₿ BTC           │  │  € EUR         │   │
│  │  $1,250.00       │  │  0.02300000 BTC  │  │  €890.00       │   │
│  │  [Send] [History]│  │  [Send] [History]│  │  [Send][History│   │
│  └──────────────────┘  └──────────────────┘  └────────────────┘   │
│                                                                    │
│  Recent Activity (all wallets)                                     │
│  ─────────────────────────────────────────────────────────────    │
│  ▼ Sent    200 USD  →  bob        Feb 26  2:14 PM    completed     │
│  ▲ Received 0.002 BTC  ←  carol   Feb 25  9:00 AM    completed     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Add Wallet modal** triggered by [+ Add Wallet]:

```
┌──────────────────────────────────────┐
│  Add a new wallet                    │
│                                      │
│  Currency   ┌──────────────────────┐ │
│             │ USD ▾                │ │  ← USD / EUR / GBP / BTC
│             └──────────────────────┘ │
│                                      │
│  Opening    ┌──────────────────────┐ │
│  Balance    │ 0.00                 │ │
│             └──────────────────────┘ │
│                                      │
│  [Cancel]              [Create]      │  ← POST /users/{id}/wallets/
└──────────────────────────────────────┘
  409 → "You already have a USD wallet"
```

---

### 4. Transfer Flow — Quote & Confirm (2-Phase)

The transfer uses a **Quote → Confirm** pattern so the user sees the
exchange rate before committing real money.

#### Step 1 — Fill in Transfer Details

```
┌────────────────────────────────────────────────────────────────────┐
│  Send Money                                                        │
│                                                                    │
│  From wallet   ┌──────────────────────────────────────────────┐   │
│                │ 💵 USD  —  balance: $1,250.00  ▾             │   │
│                └──────────────────────────────────────────────┘   │
│                                                                    │
│  To wallet ID  ┌──────────────────────────────────────────────┐   │
│                │ Paste destination wallet ID                   │   │
│                └──────────────────────────────────────────────┘   │
│                                                                    │
│  Amount        ┌──────────────────────────────────────────────┐   │
│                │ 108.00                                        │   │
│                └──────────────────────────────────────────────┘   │
│                  Sending in: USD                                   │
│                                                                    │
│  Note (opt.)   ┌──────────────────────────────────────────────┐   │
│                │ rent                                          │   │
│                └──────────────────────────────────────────────┘   │
│                                                                    │
│                              [Get Quote →]                        │
└────────────────────────────────────────────────────────────────────┘
```

> "Get Quote" is a **client-side calculation** using the hard-coded rates
> (or a future `GET /rates` endpoint). No funds move yet.

---

#### Step 2 — Review Quote

```
┌────────────────────────────────────────────────────────────────────┐
│  Transfer Quote                              ⏱ Rate locked 59s    │
│  ─────────────────────────────────────────────────────────────    │
│                                                                    │
│  You send          108.00 USD                                      │
│  Recipient gets    100.00 EUR                                      │
│                                                                    │
│  Exchange rate     1 USD = 0.9259 EUR                              │
│  (Rate: 1 USD = $1.00, 1 EUR = $1.08)                             │
│                                                                    │
│  Note              rent                                            │
│                                                                    │
│  From wallet       💵 USD  ···a3f2                                │
│  To wallet              ···b9c1                                   │
│                                                                    │
│  ─────────────────────────────────────────────────────────────    │
│                                                                    │
│  [← Back]                         [Confirm & Send]                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

> The countdown timer (60 s) is purely cosmetic in v1 — it signals how
> long rates are considered fresh. On expiry, the quote refreshes before
> re-enabling Confirm.  
> Clicking **Confirm & Send** → `POST /transfers`

---

#### Step 3 — Success / Failure

```
Success ──────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────────────────┐
│                    ✅  Transfer Complete                           │
│                                                                    │
│   You sent         108.00 USD                                      │
│   Recipient got    100.00 EUR                                      │
│   Transaction ID   txn_4e2a…                                       │
│   Status           completed                                       │
│                                                                    │
│          [View History]          [Send Another]                    │
└────────────────────────────────────────────────────────────────────┘

Failure states ───────────────────────────────────────────────────────

  400  Insufficient funds
       "You only have $50.00 USD available."

  400  Same wallet
       "Source and destination wallets cannot be the same."

  403  Not your wallet
       "You can only send from your own wallets."

  401  Session expired
       Redirect to Login with message "Session expired — log in again."
```

---

### 5. Transaction History

Accessed via **[History]** button on a wallet card or the nav.

```
┌────────────────────────────────────────────────────────────────────┐
│  💵 USD Wallet  ···a3f2        Transaction History    [← Back]    │
│                                                                    │
│  Filter:  [All ▾]    [All Status ▾]    [Search note…]             │
│                                                                    │
│  ─────────────────────────────────────────────────────────────    │
│  ▼ SENT   Feb 26 2:14 PM                              completed    │
│    To: ···b9c1 (EUR)      108.00 USD  →  100.00 EUR               │
│    Note: rent                                                      │
│                                                                    │
│  ▲ RECEIVED  Feb 25 9:00 AM                           completed    │
│    From: ···c7d4 (BTC)    0.00200000 BTC  →  104.00 USD           │
│                                                                    │
│  ─────────────────────────────────────────────────────────────    │
│                                                                    │
│                 [Load more]   (limit=50, server-side)              │
└────────────────────────────────────────────────────────────────────┘
```

API call: `GET /wallets/{wallet_id}/transactions?limit=50`

Direction is determined client-side:
- `from_wallet_id == myWalletId` → **SENT** (▼)
- `to_wallet_id   == myWalletId` → **RECEIVED** (▲)

---

## Component Tree (React)

```
App
├── AuthProvider  (JWT in memory, refresh logic)
│
├── /register  →  RegisterPage
├── /login     →  LoginPage
│
└── (authenticated routes)
    ├── Layout
    │   ├── NavBar  (user name, log out)
    │   └── <Outlet>
    │
    ├── /dashboard  →  DashboardPage
    │   ├── WalletCard[]
    │   │   ├── BalanceDisplay
    │   │   ├── SendButton   → navigate(/transfer?from=walletId)
    │   │   └── HistoryButton → navigate(/wallets/:id/transactions)
    │   ├── AddWalletModal
    │   └── RecentActivityList
    │
    ├── /transfer  →  TransferPage
    │   ├── TransferForm    (step 1)
    │   ├── QuoteReview     (step 2)
    │   └── TransferResult  (step 3)
    │
    └── /wallets/:id/transactions  →  TransactionHistoryPage
        ├── TransactionFilter
        └── TransactionList
            └── TransactionRow[]
```

---

## API ↔ UI Mapping

| Screen / Action | Method | Endpoint |
|---|---|---|
| Register | POST | `/auth/register` |
| Login | POST | `/auth/token` |
| Load wallets | GET | `/users/{id}/wallets/` |
| Get single wallet | GET | `/users/{id}/wallets/{wid}` |
| Add wallet | POST | `/users/{id}/wallets/` |
| Confirm transfer | POST | `/transfers` |
| Load transactions | GET | `/wallets/{id}/transactions?limit=50` |

---

## State Management

```
AuthStore
  currentUser: { id, username, email }
  token: string | null          ← in-memory only (not localStorage)

WalletStore
  wallets: Wallet[]
  loading: boolean
  error: string | null

TransferStore
  step: "form" | "quote" | "result"
  form: { fromWalletId, toWalletId, amount, note }
  quote: { sendAmount, receiveAmount, rate, currency, expiresAt }
  result: Transaction | null

TransactionStore
  byWalletId: Map<walletId, Transaction[]>
  loading: boolean
```

---

## Exchange Rate Display Logic

Rates are hard-coded in `services/currency_service.py`.  
Mirror them in the frontend constants until a `GET /rates` endpoint exists:

```ts
// rates.ts
const RATES_TO_USD: Record<Currency, number> = {
  USD: 1,
  EUR: 1.08,
  GBP: 1.27,
  BTC: 52000,
};

function getQuote(amount: number, from: Currency, to: Currency) {
  if (from === to) return { receiveAmount: amount, rate: 1 };
  const inUSD = amount * RATES_TO_USD[from];
  const receiveAmount = inUSD / RATES_TO_USD[to];
  const rate = RATES_TO_USD[from] / RATES_TO_USD[to];
  return { receiveAmount, rate };
}
```

The countdown timer resets to 60 s each time `getQuote` is called.  
On expiry the form re-calculates and shows a toast:  
_"Rate refreshed — please review before confirming."_

---

## Error Handling Strategy

| HTTP Status | User-facing message | Behaviour |
|---|---|---|
| 400 | Inline below form | Stay on page, highlight field |
| 401 | "Session expired" | Redirect to /login |
| 403 | "Not authorised" | Inline error |
| 404 | "Not found" | Inline error |
| 409 | "Already exists" | Inline error |
| 422 | "Invalid input" | Show field-level Pydantic errors |
| 5xx | "Something went wrong" | Toast + retry button |

---

## Future UI Additions (aligned with CONTRIBUTING.md)

| Feature | UI impact |
|---|---|
| Idempotency keys | Generate UUID per Submit click; disable button on inflight |
| Refresh tokens | Silent token refresh in `AuthProvider` before expiry |
| Pagination | Replace [Load more] with cursor-based infinite scroll |
| Rate limiting | Show retry-after countdown on 429 |
| BTC display | Always show 8 decimal places; abbreviate in list view |
| MFA | Extra step after login (TOTP code input) |
