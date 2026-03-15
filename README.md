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

---

## database migrations (Alembic)

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html). Migration files live in `alembic/versions/`.

### common commands

**Apply all pending migrations** (run this after pulling new changes)
```bash
alembic upgrade head
```

**Undo the last migration**
```bash
alembic downgrade -1
```

**Undo all migrations** (back to empty schema)
```bash
alembic downgrade base
```

**Check current migration state**
```bash
alembic current
```

**View migration history**
```bash
alembic history --verbose
```

### adding a new migration

After changing a model in `app/models/`, generate a migration automatically:
```bash
alembic revision --autogenerate -m "describe_your_change"
```

Review the generated file in `alembic/versions/` before applying — add any data cleanup SQL if needed (e.g. deduplication before adding a unique constraint). Then apply:
```bash
alembic upgrade head
```

### notes

- If you have a **local PostgreSQL** running on port `5432`, it will conflict with the Docker DB. Stop it first:
  ```bash
  brew services stop postgresql@15   # adjust version as needed
  ```
- Alembic tracks applied migrations in the `alembic_version` table inside the DB — running `upgrade head` multiple times is safe, it only applies what's new.
- Migration files must be committed to git so teammates and production deployments can apply the same changes.