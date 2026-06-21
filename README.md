# Fitness Tracker

A self-hosted fitness & nutrition tracker. **Phase 0 (scaffold) + Phase 1 (calorie engine)**:
user accounts, a profile, settings, and a Kalorienbedarf calculator built on Mifflin-St Jeor
BMR × an occupational activity factor, with in-app explainer screens (EN/DE). Food logging and
workout tracking come in later phases.

> **Not medical or nutrition advice.** The calorie engine includes a safety floor and an
> excessive-deficit warning, but it is an engineering tool, not a coach.

## Stack

- **Backend:** Python 3.12 + FastAPI, SQLAlchemy 2.0 (`Mapped`/`mapped_column`), Alembic,
  PostgreSQL. Precise values are `Decimal`, never `float`.
- **Frontend:** React + Vite + TypeScript + SCSS, built as an installable **PWA** (web manifest
  + service worker), with **react-i18next** for English + German and a visible language switcher.
- **Local dev:** Docker Compose (Postgres + API). **Production:** systemd + uvicorn behind nginx
  against the host's system Postgres (Docker is dev-only).

## Layout

```
backend/
  calories/      # PURE calorie engine (BMR, activity factors, goal target, floor) — no DB
  api/           # FastAPI routers (auth, profile, settings, calories, health)
  persistence/   # SQLAlchemy Base, models (users/profiles/settings), repository, types
  auth/          # bcrypt + JWT (HS256)
  alembic/       # migrations (0001 = explicit frozen baseline)
frontend/        # React + Vite PWA, i18next (en/de), screens + explainers
tests/           # pytest (in-memory SQLite)
```

## Run locally

Backend + database (Docker):

```bash
cp .env.example .env
# set FERNET_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
docker compose up --build           # Postgres + API on http://localhost:8000
```

Or run the API directly against a local Postgres / SQLite:

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
export FERNET_KEY=... DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/fitness
.venv/bin/alembic upgrade head
.venv/bin/uvicorn backend.main:app --reload      # /api/docs for the OpenAPI UI
```

Frontend:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api + /health to :8000
npm run build        # production build -> frontend/dist (served by nginx in prod)
```

Tests:

```bash
.venv/bin/pytest      # calorie engine (BMR, multipliers, goals, floor) + API tests
```

The SPA calls the API same-origin at `/api`; in dev, Vite proxies `/api` and `/health` to the
backend target (override with `VITE_API_TARGET`).

## Deployment (production)

Runs at **https://fitness-tracker.kipphard.com** on the Hetzner box, **not** in Docker — it
follows the host's pattern: a **systemd** service running `uvicorn` on `127.0.0.1:8003` behind
nginx, against the host's **system PostgreSQL** (a dedicated `fitness` role + DB).

- **Service:** `/etc/systemd/system/fitness-tracker.service` (runs `alembic upgrade head` as
  `ExecStartPre`, then uvicorn). Code in `/opt/fitness-tracker`; secrets in
  `/opt/fitness-tracker/.env` (chmod 600, server-only — never committed).
- **nginx vhost:** `fitness-tracker.kipphard.com` → `127.0.0.1:8003`, serving the built SPA from
  `/opt/fitness-tracker/frontend/dist`, reusing the shared `*.kipphard.com` Cloudflare origin
  cert (no per-vhost `real_ip_header` — it is set globally).
- **Push-to-deploy:** `.github/workflows/deploy.yml` builds the SPA, rsyncs to the server and
  restarts the service on push to `main`. Needs repo secret `DEPLOY_SSH_KEY`; GitHub Actions
  billing must be active. The frontend is built in CI (no Node on the server).
- **Manual deploy:** rsync the repo to `/opt/fitness-tracker` (excluding
  `.git/.venv/__pycache__/.env/node_modules`), then on the server:
  `.venv/bin/pip install -e . && .venv/bin/alembic upgrade head && systemctl restart fitness-tracker`.
  Validate any new migration on a throwaway `fitness_migtest` DB first.
