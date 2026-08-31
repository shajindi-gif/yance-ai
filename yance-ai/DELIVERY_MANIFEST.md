# Delivery manifest

| Requested item | Delivered at |
|---|---|
| 1. Complete runnable backend | `app/`, `pyproject.toml`, `Dockerfile`, `tests/` |
| 2. Dev/prod Compose | `docker-compose.dev.yml`, `docker-compose.prod.yml` |
| 3. Required APIs | `app/api/routes/` |
| 4. SQLAlchemy + Alembic | `app/models/`, `alembic/` |
| 5. PostgreSQL + pgvector | Dev image, Vector model/store, migration |
| 6. Alibaba RDS/OSS production config | `.env.production.example`, `ops/aliyun/`, deployment guide |
| 7. OSS presigned upload | `app/services/oss.py`, document API |
| 8. Multi-tenant + RBAC | JWT principal, tenant-scoped queries, roles, provisioning API |
| 9. Orders/payments/invoices skeleton | Models, schemas and `commerce.py` |
| 10. LLM provider/router | `app/services/llm/` |
| 11. Evals/golden cases | `evals/` |
| 12. Product analytics | `AnalyticsEvent`, `/analytics/events` |
| 13. Structured/agent logging | structlog middleware, `AgentRun`, agent-run API |
| 14. Product/release system | `.github/`, `CHANGELOG.md`, `docs/product/`, `docs/releases/` |
| 15. GitHub Actions | `.github/workflows/ci.yml`, `deploy-example.yml` |
| 16. Nginx | `nginx/conf.d/default.conf`, `nginx/https.conf.example` |
| 17. Environment examples | `.env.example`, `.env.production.example` |
| 18. Tomorrow deployment guide | `明日部署手册.md` |
| 19. Pre-deployment checklist | `部署前检查清单.md` |
| 20. Go-live acceptance checklist | `上线验收清单.md` |

## Verification record

- Python 3.12 dependency installation: passed
- Ruff lint/format: passed
- Pytest: 5 passed
- Golden case validation: 2 passed
- Docker image build: passed
- Dev Compose + PostgreSQL 16 + pgvector: passed
- Alembic upgrade/check/downgrade/re-up: passed, no model drift
- Health/readiness and core API flow: passed
- Two-tenant provisioning and cross-tenant 404: passed

OSS upload was validated structurally but not executed against a real Bucket because no production
credentials are included. DNS, TLS, RDS and OSS console acceptance must be completed with the three
Chinese checklists during deployment.
