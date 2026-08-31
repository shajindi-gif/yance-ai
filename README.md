# Yance.ai — Policy Intelligence Agent SaaS

Evidence-Grounded 政策匹配与申报 Agent 平台。

## Repository Structure

```
yance/
├── yance-ai/     # FastAPI backend (Python 3.12, SQLAlchemy 2, pgvector)
├── website/      # Next.js 14 frontend (TypeScript, App Router)
└── benchmark/    # Policy Engine evaluation benchmarks
```

## Quick Start

```bash
# Backend
cd yance-ai
cp .env.example .env  # fill in real values
pip install .
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd website
npm install
npm run dev
```

## Environment Variables

See `.env.example`. Never commit `.env` or `env.prod`.

## Documentation

- Backend docs: `yance-ai/docs/`
- Operations: `yance-ai/docs/PRODUCTION_OPS.md`
