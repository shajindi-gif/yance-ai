# Technology Stack

Status: **Implemented**.

| Layer | Current technology | Repository evidence |
|---|---|---|
| Web | Next.js 16.3.4, React 19.2.8, TypeScript | [`website/package.json`](../../website/package.json) |
| API | Python 3.12, FastAPI, Pydantic Settings | [`yance-ai/pyproject.toml`](../../yance-ai/pyproject.toml) |
| Persistence | SQLAlchemy 2, Alembic, PostgreSQL | [`yance-ai/app/core/db.py`](../../yance-ai/app/core/db.py) |
| Retrieval | PostgreSQL full-text search + pgvector | [`yance-ai/app/services/policies/retrieval.py`](../../yance-ai/app/services/policies/retrieval.py) |
| LLM | provider-neutral interface; Qwen, DeepSeek and other OpenAI-compatible endpoints | [`yance-ai/app/services/llm/`](../../yance-ai/app/services/llm/) |
| Artifacts | deterministic DOCX/PDF/XLSX/JSON renderer | [`yance-ai/app/services/applications/artifacts.py`](../../yance-ai/app/services/applications/artifacts.py) |
| Document intelligence | pypdf, PyMuPDF/Tesseract OCR, python-docx, openpyxl, bounded HTML/text parsers, ClamAV | [`yance-ai/app/services/documents/`](../../yance-ai/app/services/documents/) |
| Runtime | Docker; separate API, migration, worker, database services | [`yance-ai/docker-compose.prod.yml`](../../yance-ai/docker-compose.prod.yml) |
| CI | GitHub Actions: lint, contract, migration, tests, eval, audits, builds | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) |

Versions are locked in application manifests/lockfiles. This table is an implementation inventory, not a support-lifecycle or certification claim.
