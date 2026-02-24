# banking-app-021926

Code up a banking app that
- can be spun up using docker compose
- users can transfer money between wallets
- 4 hard-coded different currencies including cryptocurrency 
- user can get transactions

The rest is up to you. You can go as deep as you want

## quickstart

### prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Python 3.11+

---

### 1. clone the repo
```bash
git clone <your-repo-url>
cd banking-app-021926
```

### 2. create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
```

### 3. install dependencies
```bash
pip install -r requirements.txt
```

### 4. start the app
```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432` (production DB)
- **FastAPI** on port `8000`

API: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

---

### 5. running tests

Tests run against a dedicated PostgreSQL test database on port `5433`, completely separate from the production DB.

**Start the test database**
```bash
docker compose up db_test -d
```

**Run all tests**
```bash
.venv/bin/pytest tests/ -v
```

**Run a specific file**
```bash
.venv/bin/pytest tests/test_endpoints.py -v
.venv/bin/pytest tests/test_transfer.py -v
```

**Override the test DB URL** (optional)
```bash
TEST_DATABASE_URL=postgresql://user:pass@host:5432/mydb pytest tests/ -v
```