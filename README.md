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

Second local batch: fenced Agent attempts, per-recipient deadline email outbox and worker shutdown checks. 220 backend tests passed; additive migration 0028 is **not deployed**. See [validation](docs/v2-reliability-report-20261023.md) and [release constraints](docs/v2-reliability-runbook-20261023.md).

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

## Website design release — 2026-10-25

The website at yance.ai runs source `68a4b46` with Next16.4.3. The original website backup and a tested old-UI rollback build with the same security update are retained. Production backend remains e58a7c4; V2 evidence features activate only when the backend declares support. See [actual release and rollback](docs/website-release-20261025.md).


## Website audience and pricing release — 2026-10-27

Current production website source is `e549923` (web-20261026-01), including enterprise audience, clearly marked usage scenarios, feedback entrance and pricing presentation. Ten public pages and mobile passed final read-only verification. The previous website backup and restored copy remain available; backend/database/prices are unchanged. See [actual release and rollback](docs/website-release-20261026.md).


## Historical company-wide local candidate — 2026-10-28

Candidate `1753fa9` fixes manual revision metering, server-side product availability and feedback recovery/status, with safe post-login return paths. At that checkpoint it was **not deployed**. It has since been released as bd0ef29; see the current production record below. See [audit](docs/company-wide-optimization-audit.md), [plan](docs/company-wide-optimization-plan.md), [validation](docs/company-wide-optimization-test-report.md) and [release constraints](docs/company-wide-optimization-release.md).


## Full production release — 2026-10-28

The company-wide implementation1753fa9 is live as fixed release source `bd0ef29`, website `full-20261028-01`, backend/worker `bd0ef29`, database `20261027_0033`. Final backup restoration and original-row preservation passed; ten public pages and mobile passed read-only verification at15:15 Asia/Shanghai. Five legacy nullable-schema differences remain explicitly accepted, and task email is disabled while existing API login email is retained. Recovery readiness failure extended maintenance; see the complete [production record and fallback](docs/full-release-20261028.md), including remaining supplier/real-business verification limits. Earlier local-only descriptions are historical.


## Growth release — 2026-10-29

Production website `growth-20261029-01`, API/worker source `4587e34` (verified business implementatione25ab04), database unchanged0033. Original industry imagery and checkout retry protection are live. Fresh backup restoration and public desktop/mobile checks passed; prior version and rollback scripts retained. See [actual release and limits](docs/growth-release-20261029.md).


## Supplied imagery website release — 2026-10-29

Website `images-20261029-01` / source `5b5c1f7` (page implementationb3d1627) is live. Six user-supplied images replace generated scenes; desktop/mobile public checks passed. Backend remains4587e34, no database operations. Verified previous website backup retained. See [release and rollback](docs/images-release-20261029.md).

## Phone authentication candidate — 2026-10-29 (not deployed)

Tencent SMS registration/login and authenticated phone binding have passed 252 isolated backend tests and two local API browser journeys. Real delivery is blocked by insufficient SMS package balance; production SMS stays disabled and email login remains available. See [implementation, evidence and release constraints](docs/sms-auth-20261029.md).
