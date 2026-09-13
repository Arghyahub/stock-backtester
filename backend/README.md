# Stock Backtester API

FastAPI backend for Anomaly Trading V2. It stores daily prices, curated
sector-to-instrument mappings, and the latest published research results.

## Requirements

- Python 3.14+
- PostgreSQL
- [`uv`](https://docs.astral.sh/uv/)

## First-time setup

```bash
cp .env.example .env
```

Set `DATABASE_URL` and a long random `JWT_SECRET` in `.env`. Both
`postgresql://...` and `postgresql+psycopg://...` connection strings work.

```bash
uv sync
```

For an **existing** database that already has the original application tables,
add only the V2 tables:

```bash
uv run alembic upgrade head
```

For a **new empty** database, create the complete current schema once and mark
the initial migration as applied:

```bash
uv run python -c 'from app.db.database import Base, engine; import app.db.models; Base.metadata.create_all(bind=engine)'
uv run alembic stamp head
```

## Create the first admin

Register through the running API, then promote the account once in PostgreSQL.
New registrations are deliberately general users.

```bash
curl -X POST http://localhost:8000/user/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}'
```

```sql
UPDATE users SET user_type = 'admin' WHERE email = 'YOUR_EMAIL';
```

## Run locally

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Admin workflow

1. Sign in at frontend `/admin` with the promoted admin account.
2. Add **Anomaly Trading** if it is not already present.
3. Track sector history.
4. Add curated stock and ETF ticker mappings for each sector.
5. Refresh mapped data after market close.
6. Compute V2. A successful run replaces older published results but retains
   daily price history.

Public `/anomaly` endpoints are read-only; admin mutations require an admin
JWT.

## Checks

```bash
uv run pytest -q
```
