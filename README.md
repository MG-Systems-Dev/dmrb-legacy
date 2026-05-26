# DMRB Legacy

**The DMRB (Digital Make Ready Board)** — a FastAPI + React application for **apartment turnover** operations: board views, task pipelines, CSV imports from property-management reports, exports, optional AI assistance, and work-order validation workflows. Data lives in **PostgreSQL** (no ORM; repositories + raw SQL).

## Requirements

- Python 3.11+ (3.13 used in development)
- PostgreSQL database and a `DATABASE_URL` connection string

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set `DATABASE_URL` in the environment (see `config/settings.py` for all supported keys). Do not commit secrets.

```bash
cd frontend && npm install && npm run build
cd ..
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Commands

| Action | Command |
|--------|---------|
| Build frontend | `cd frontend && npm install && npm run build` |
| Run app | `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000` |
| Tests | `pytest tests/` |
| Midnight automation (scheduled jobs) | `python scripts/run_midnight_automation.py` (optional `--date YYYY-MM-DD`) |

## Configuration

Copy `.env.example` → `.env` and fill in `DATABASE_URL` before starting locally.

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `OPENAI_API_KEY` | — | Required for the AI Agent screen only |

Full table and architecture rules: **[CLAUDE.md](CLAUDE.md)**. Operator-facing flow diagrams: **[docs/LEGACY_APP_FLOW.md](docs/LEGACY_APP_FLOW.md)**.

## Project layout

| Path | Purpose |
|------|---------|
| `api/main.py` | FastAPI entrypoint + SPA host |
| `frontend/` | React SPA |
| `ui_archive/` | Archived Streamlit reference code |
| `services/` | Orchestration and workflows |
| `db/repository/` | Database access |
| `domain/` | Pure business logic |
| `db/migrations/` | Incremental schema migrations (applied at startup) |

## Deploy to Railway

This repo ships a `nixpacks.toml` and `railway.json` so Railway can build and run the full stack (Python API + React SPA) as a single service.

### One-time setup

1. **Create the service.** In Railway, New Project → Deploy from GitHub repo → point at this repo. Nixpacks will auto-detect the config.
2. **Attach a Postgres.** Either use Railway's Postgres plugin (sets `DATABASE_URL` automatically) or paste your Supabase pooled connection string into `DATABASE_URL` as a service variable.
3. **Set required env vars** (Service → Variables):

   | Variable | Required | Value |
   |---|---|---|
   | `DATABASE_URL` | ✅ | Postgres connection string (auto if using Railway Postgres plugin) |
   | `OPENAI_API_KEY` | optional | Only if enabling the AI Agent page |

   > **`.env` vs Railway Variables:** `.env` is for local dev only and is never deployed to Railway. Set production values in Railway's Variables tab.

4. **Health check.** Railway probes `/healthz` — already configured in `railway.json`.

### What happens on each deploy

1. Nixpacks installs Python 3.11 and Node 20.
2. `pip install -r requirements.txt` + `npm ci` in `frontend/`.
3. `npm run build` produces a fresh `frontend/dist/`.
4. `uvicorn api.main:app` starts on `$PORT` with `--proxy-headers`.
5. FastAPI's startup hook runs `ensure_database_ready()`, applying any pending migrations in `db/migrations/` idempotently.

## Documentation

- **[docs/IMPORT_REBUILD_ORDER.md](docs/IMPORT_REBUILD_ORDER.md)** — import sequencing and rebuild contract
- **[AGENTS.md](AGENTS.md)** — notes for AI assistants and multi-checkout (dev vs prod)
- **[HARDENED_MIGRATION_PLAN.md](HARDENED_MIGRATION_PLAN.md)** — migration / hardening planning

## License

See the [`LICENSE`](LICENSE) file in the repository root for terms of use.
