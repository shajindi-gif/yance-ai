# Yance.ai — Policy Intelligence Agent SaaS

Evidence-Grounded 政策匹配与申报 Agent 平台。

## Repository Structure

```
yance/
├── yance-ai/     # FastAPI backend (Python 3.12, SQLAlchemy 2, pgvector)
├── website/      # Next.js 16 frontend (TypeScript, App Router)
└── benchmark/    # Policy Engine evaluation benchmarks
```

## 2026-10-20 audit and release status

The current audit and local changes are documented in [docs/audit.md](docs/audit.md), [upgrade-plan](docs/upgrade-plan.md), [test-report](docs/test-report.md) and [release-runbook](docs/release-runbook.md). The backend and database migrations were authorized and deployed on 2026-10-21; see [production release evidence](docs/backend-release-20261021.md). The current website source is also live. The release workflow only verifies/packages source; production is activated through an explicit reviewed release procedure.

## V2 evidence workspace — local candidate (2026-10-23)

The first batch adds a source-bound eligibility matrix, persistent evidence-gap checklist, and stale-approval/concurrent-edit safeguards. Local isolated tests passed; this batch has not been deployed. See [implementation and validation](docs/v2-first-batch-report-20261023.md), [gap map](docs/v2-gap-map-20261023.md), and [data contract](docs/v2-evidence-contract.md).

## Quick Start

### Option A — Docker (recommended, one command)

```bash
# Backend: PostgreSQL 16 + pgvector, auto schema migration, API + agent worker
cd yance-ai
make dev-up          # first run copies .env.example → .env, builds and starts the stack
# API docs: http://localhost:8000/docs
```

Frontend:

```bash
cd website
npm install
npm run dev          # http://localhost:3000, proxies /api/* to localhost:8000
```

### Option B — Native Python

Requires PostgreSQL 16 with the `pgvector` extension.

```bash
cd yance-ai
cp .env.example .env  # fill in real values (DATABASE_URL at minimum)
pip install .
alembic upgrade head
uvicorn app.main:app --reload
```

### Tests

```bash
cd yance-ai
APP_ENV=test DATABASE_URL=postgresql+psycopg://.../yance_test \
YANCE_TEST_DATABASE_ACK=yance_test pytest
# Use a freshly created, migrated, disposable database; fixtures mutate it.
```

> Note: core API and database run out of the box. LLM-powered agents, payments
> (Alipay/WeChat Pay) and transactional email require their respective API keys
> in `.env` and degrade gracefully (feature flags / 503) when unconfigured.

## Environment Variables

See `.env.example`. Never commit `.env` or `env.prod`.

## Documentation

- Backend docs: `yance-ai/docs/`
- Operations: `yance-ai/docs/PRODUCTION_OPS.md`
- Investor demo: `/demo` after running `python scripts/seed_investor_demo.py`
- Engineering data room: `docs/data-room/`
