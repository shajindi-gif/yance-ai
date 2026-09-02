# Phase 1 Implementation Plan — P0 Stability & Security

## Objective

Close deterministic production blockers before design or product expansion:
payment fabrication, financial configuration exposure, tenant scope, schema
drift, unsafe PDF rendering, eligibility hard gates, and false public claims.

## Change slices

1. Commerce safety: demo routes default-off and impossible in production,
   server-owned pricing, provider-only payment creation, invoice persistence fix.
2. Tenant safety: tenant-filter operational task view and global/private policy
   visibility filter.
3. Configuration: track sanitized environment examples, remove financial
   defaults, add an accurate root security policy.
4. Data: forward migration for Task/Deliverable ORM drift; no destructive column
   removal in this phase.
5. Rendering and decision safety: escape untrusted HTML, deny renderer network
   and file access, make safety/compliance criteria blocking, require review.
6. Truth and release controls: remove unsupported UI claims and establish root
   CI with security and migration checks.

## Files

- `yance-ai/app/core/config.py`
- `yance-ai/app/api/routes/{commerce,demo_match,payments,policy_engine,tasks}.py`
- `yance-ai/app/services/{report/pdf,invoice/generator,policy_engine/deterministic}.py`
- `yance-ai/alembic/versions/20260902_0009_*.py`
- `yance-ai/tests/`
- `website/app/{checkout,dashboard,reports,security,privacy,downloads}/`
- `.github/workflows/ci.yml`, `.env.example`, `SECURITY.md`

## Verification

- Negative tests for production demo routes, client price tampering, tenant
  access, unpaid delivery, HTML/URL payloads, and blocking eligibility criteria.
- PostgreSQL base-to-head and ORM schema comparison.
- Ruff, pytest, frontend type/build, dependency/secret scan.
- Manual authenticated smoke of login, company, order, policy evaluation and
  denied demo payment.

## Rollback

All database work is additive. Application rollback can ignore the added
columns; downgrade is reserved for isolated non-production environments. No
existing user or business record is deleted.
