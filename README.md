# banking-app-021926

Code up a banking app that
- can be spun up using docker compose
- users can transfer money between wallets
- 4 hard-coded different currencies including cryptocurrency 
- user can get transactions

The rest is up to you. You can go as deep as you want


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

## docker compose
architecture design 
python(Java, go, Node)
PostgreSQL + FastAPI services, 
Numeric(28,8)
SQLite for tests

## one user should not able to change other user's money


## precent two concurrent transfers on same wallet
use SELECT FOR UPDATE
Add a row-level database lock when fetching the wallets, so the second thread blocks until the first commits

With sorting by IDs — both threads lock in the same order
Say wallet_alice_id = "aaa" and wallet_bob_id = "bbb". Sorted alphabetically: ["aaa", "bbb"] — alice always first.

## one user submit multi times, should be counted as once 


## get transactions with pagination or better way for it?