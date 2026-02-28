# Contributing & Development Notes

## local development setup

```bash
git clone <your-repo-url>
cd banking-app-021926

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Start the test DB and run tests:
```bash
docker compose up db_test -d
pytest tests/ -v
```

---

## known dependency quirks

### passlib + bcrypt incompatibility

**Symptom:**
```
ValueError: password cannot be longer than 72 bytes, truncate manually
```
Even with short passwords (e.g. `"testpass123"`).

**Root cause:**  
`passlib 1.7.4` was written before `bcrypt 4.0.0`. In bcrypt 4.x, the API changed to raise an explicit error when passwords exceed 72 bytes. However, passlib 1.7.4 passes the password to bcrypt in a format that bcrypt 4.x misinterprets, making it think the password is too long even when it isn't.

**Fix applied:**  
- Pin `bcrypt<4.0.0` in `requirements.txt`
- Added `bcrypt__truncate_error=False` to `CryptContext` in `app/auth.py` as a fallback

**Long-term fix:**  
When `passlib 1.8+` is released (or switch to [`pwdlib`](https://github.com/frankie567/pwdlib)), remove the `bcrypt<4.0.0` pin.

---

## architecture decisions

### why PostgreSQL for tests (not SQLite)?
SQLite silently ignores `SELECT FOR UPDATE` (row-level locking), which is a core part of the concurrent transfer safety logic. Using a real PostgreSQL instance for tests ensures that locking behavior is actually validated.

### why integers/Decimal for money?
Floats cannot represent many decimal values exactly in binary (e.g. `0.1 + 0.2 != 0.3`). All amounts are stored as `NUMERIC(28,8)` in PostgreSQL and handled as `Decimal` in Python to avoid rounding errors and audit failures.

### why SELECT FOR UPDATE with sorted wallet IDs?
Two concurrent transfers between the same pair of wallets (A→B and B→A simultaneously) can deadlock if each locks in a different order. Sorting wallet IDs before acquiring locks guarantees both transactions always lock in the same order, preventing deadlock.


### folder info
app/
  main.py          ← 1. Entry point. App is created, routers attached, DB tables created
  routers/         ← 2. HTTP layer. Receives request, calls auth + schemas + services
  auth.py          ← 3. Who is this user? Validate JWT, return User
  schemas/         ← 4. Is the data valid? Validate in, serialize out
  services/        ← 5. Business logic. What should actually happen?
  models/          ← 6. What does the data look like in the DB?
  database.py      ← 7. How do we connect to PostgreSQL?
  config.py        ← 8. Settings (DB URL, JWT secret, etc.) — used by everyone

  config.py is special — it's at the bottom but it's actually read by everything. It's the foundation that all other layers depend on, not a step in the request flow.
  

Higher = closer to the client (HTTP, JSON)
Lower  = closer to the database (SQL, rows)

main.py    ▲ client-facing
routers    │
auth.py    │
schemas    │
services   │
models     │
database   │
config.py  ▼ infrastructure





---

## future improvements

- [ ] **Idempotency keys** — prevent duplicate transfers if a user submits the same request twice (e.g. double-click). Store a client-provided `idempotency_key` and 
return the existing transaction if the key has already been used.
generate key
send request 
success? -> Done
Failed, retryable error?
Yes, wait(backoff + jitter)
retry with SAME key -> repeat
max retries hit
Throw error to UI 

- [ ] **Alembic migrations** — replace `Base.metadata.create_all()` with proper Alembic migration scripts for schema versioning.
- [ ] **Refresh tokens** — current JWTs are short-lived (60 min). Add a refresh token flow so users don't get logged out.
- [ ] **Passlib upgrade** — once `passlib 1.8+` is stable, remove the `bcrypt<4.0.0` pin.
- [ ] **Transaction pagination** — current `/wallets/{id}/transactions` uses a `limit` query param. Consider cursor-based pagination for large transaction histories.
- [ ] **Rate limiting** — add rate limiting on `/auth/token` to prevent brute-force attacks.
- [ ] **Audit log** — record who initiated each transfer (requester user ID) directly in the `transactions` table.







## docker compose
architecture design 
python(Java, go, Node)
PostgreSQL + FastAPI services, 
Numeric(28,8)


## money precision
use integers(fixed point arithmetic) for money, Never floats. 
- rounding errors
- inconsistent comparision(balance == 100.00 may fail)
- regulartory and audit failures 

store amounts in the smallest currency unit(cents, pence, paisa, etc)
- insead of balance = 12.50 # dollars
- balance = 1250 # cents
- 1250 + 50 = 1300 # $13.00, perfect accurate
- integers are exat in binary, no precision loss

use string type to hold exact decimal representations for input parsing or diplaying formatted output("$12.50"), but never for calculation or storage 

in databases, use NUMERIC(19,4) or DECIMAL(19,4) - never FLOAT or DOUBLE 

## one user should not able to change other user's money

## precent two concurrent transfers on same wallet
use SELECT FOR UPDATE
Add a row-level database lock when fetching the wallets, so the second thread blocks until the first commits

With sorting by IDs — both threads lock in the same order
Say wallet_alice_id = "aaa" and wallet_bob_id = "bbb". Sorted alphabetically: ["aaa", "bbb"] — alice always first.

## one user submit multi times, should be counted as once 
## get transactions with pagination or better way for it?

## currency rate display for user, lock for up to 1 hour, commit later. 
same as payment process, show total amount/tex/fees, then user click submit button
User 2-phase transaction pattern at the API level! Often called "quote and confirm" or "hold and commit".



## Here are the major areas a real banking system needs to address, beyond what's already implemented:

### Security
Password policy — minimum length, complexity, breach detection (check against HaveIBeenPwned)
Token revocation — JWTs can't be invalidated after issue; need a blocklist or short expiry + refresh tokens
MFA — TOTP (Google Authenticator) or SMS for sensitive operations
Brute force protection — rate limit /auth/token, lock account after N failed attempts
Sensitive data encryption at rest — PII fields (email, name) should be encrypted in the DB, not just hashed passwords
TLS everywhere — never serve over plain HTTP in production
Audit logging — every action (who, what, when, from which IP) must be logged and tamper-proof

### Money & Transactions
Idempotency — if a client retries a transfer (network timeout, double-click), it must be counted once. Standard approach: client sends a unique idempotency_key, server deduplicates.
Double-entry bookkeeping — every debit must have a matching credit. Running balance should always reconcile to sum of all transactions. Banks use this to detect bugs and fraud.
Transaction rollback — if crediting the destination fails after debiting the source, you need compensating transactions, not silent data loss
Overdraft handling — define policy explicitly: reject, allow with fee, allow with limit
Reconciliation jobs — scheduled jobs that verify DB balances match the sum of all transactions

### Compliance & Regulation
KYC (Know Your Customer) — verify user identity before allowing large transfers
AML (Anti-Money Laundering) — flag suspicious patterns (many small transfers, sudden large transfers)
GDPR / data privacy — right to erasure, data portability, consent tracking
PCI-DSS — if you ever handle card data
Reporting — regulators require transaction reports above certain thresholds (e.g. $10,000 in the US)
Data retention — financial records must be kept for 5-7 years depending on jurisdiction

### Reliability & Operations
Database backups — point-in-time recovery, tested regularly
Circuit breakers — if currency conversion service is down, fail gracefully
Distributed tracing — trace a transfer request across all services (e.g. OpenTelemetry)
Alerts — alert on failed transactions, error rate spikes, unusual transfer volumes
Soft deletes — never hard-delete financial records; mark as inactive


### Scalability
Read replicas — offload transaction history queries to replicas
Event sourcing — store every state change as an immutable event instead of overwriting balance; makes auditing and replay trivial
Outbox pattern — reliably publish events (e.g. "transfer completed") to a message queue without losing them if the service crashes mid-operation
Sharding — when a single DB can't handle the write load

No idempotency key	Duplicate transfers on retry
No audit trail (who initiated)	Can't prove who did what
No rate limiting on auth	Brute-force vulnerability
No account lockout	Credential stuffing
No token revocation	Stolen token valid until expiry
SELECT FOR UPDATE not tested under real concurrency	Race conditions may still exist
Currency rates are hardcoded	Stale rates cause incorrect conversions


### For payment/fintech specific concepts like this:
Books:

Payment Systems in the U.S. by Carol Coye Benson — how real payment rails work
Designing Data-Intensive Applications — still applies, especially chapters on transactions

Real World References:

Stripe Engineering Blog (stripe.com/blog/engineering) — how Stripe solves exactly these problems, incredibly well written
Wise Engineering Blog — currency transfers, rate locking, exactly what you're building
Shopify Engineering Blog — idempotency, money handling at scale

Specific concepts to Google:

"Idempotency keys API payments"
"Optimistic vs pessimistic locking database"
"Saga pattern microservices"
"Double entry bookkeeping software"
"Quote and confirm payment flow"

Open Source to read:

Look at how Ledger or Lago (open source billing) handle transactions
Read Stripe's API docs — they're a masterclass in how to design payment APIs