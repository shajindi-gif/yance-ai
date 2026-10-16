# Yance.ai — Policy Intelligence Agent SaaS

Evidence-Grounded 政策匹配与申报 Agent 平台。

## Repository Structure

```
yance/
├── yance-ai/     # FastAPI backend (Python 3.12, SQLAlchemy 2, pgvector)
├── website/      # Next.js 16 frontend (TypeScript, App Router)
└── benchmark/    # Policy Engine evaluation benchmarks
```

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
pytest  # full suite (101 e2e tests) against a migrated test database:
        # APP_ENV=test DATABASE_URL=postgresql+psycopg://... pytest
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
