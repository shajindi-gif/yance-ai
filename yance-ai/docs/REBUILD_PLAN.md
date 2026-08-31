# REBUILD_PLAN.md — Yance.ai Production Rebuild

**Date:** 2026-08-09
**Version:** 0.1.0 → v1.0 (target)
**Branch:** `production-rebuild-v1`
**Backup commit:** `954b454` (pre-production-rebuild snapshot)

---

## 1. CURRENT ARCHITECTURE

### Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic
- **Database:** PostgreSQL 16 + pgvector extension
- **Embedding:** Cloudflare Workers AI (`@cf/baai/bge-large-en-v1.5`, 1024-dim)
- **LLM:** Provider abstraction — Qwen (OpenAI-compatible), DeepSeek, OpenAI, Anthropic, Mock
- **Storage:** Aliyun OSS (presigned direct upload)
- **Payments:** Alipay 电脑网站支付 (RSA2), Stripe (legacy), bank transfer
- **Invoices:** WeasyPrint PDF generation (Chinese VAT invoice layout)
- **Frontend:** Single-file SPA (`frontend/index.html`, 548 lines, vanilla HTML/CSS/JS)
- **Containerization:** Docker + Docker Compose (dev + prod profiles)
- **Reverse Proxy:** Nginx configs exist but NOT in Docker Compose
- **CI/CD:** GitHub Actions (lint → test → eval → docker build → deploy)
- **Deployment Target:** Alibaba Cloud ECS + RDS + OSS (documented in 明日部署手册.md)

### Domain Architecture (Planned)
- `yance.ai` → Marketing Website
- `app.yance.ai` → SaaS Application
- `api.yance.ai` → FastAPI Backend

### Database Schema (13 tables)
Tenant, User, Company, Document, Policy (with Vector embedding), PolicyRule, Opportunity, Application, Order, Payment, Invoice, AnalyticsEvent, AgentRun, AuditLog

### API Routes (prefix `/api/v1`)
- `/health`, `/health/ready` — Liveness + DB readiness
- `/auth/bootstrap`, `/auth/provision-tenant`, `/auth/login`, `/auth/me` — Auth
- `/tenant`, `/users` — Tenant management
- `/companies` — Company profiles CRUD
- `/documents` — OSS presigned upload
- `/policies`, `/policies/search`, `/test-embed`, `/policy-rules` — Policy library + vector search
- `/opportunities`, `/applications` — Business workflow
- `/orders`, `/payments`, `/invoices` — Commerce
- `/payments/alipay/*`, `/payments/checkout`, `/payments/webhook`, `/bank/*` — Payment processing
- `/reports/generate` — AI report generation
- `/analytics/events`, `/agent-runs` — Telemetry

---

## 2. CURRENT WORKING FEATURES

Verified via DELIVERY_MANIFEST.md (all 20 items passing):

1. Docker build succeeds (multi-stage, non-root user, healthcheck)
2. Alembic migrations run (4 migrations: initial → stripe → alipay/invoice → bank)
3. All 5 tests pass (config validation, health endpoint, route registration, JWT/password)
4. Lint passes (ruff)
5. Two-tenant provisioning with cross-tenant 404 isolation verified
6. RBAC: owner > admin > member > viewer
7. JWT auth with tenant isolation (application-level, no PostgreSQL RLS)
8. Company profile CRUD
9. Document upload via OSS presigned URLs
10. Policy CRUD + semantic search (PGVector cosine distance)
11. AI report generation (semantic search → LLM analysis)
12. Order creation + Alipay checkout
13. Alipay callback/notification handling
14. Invoice PDF generation (WeasyPrint)
15. Bank transfer payment flow
16. Analytics events + agent run tracking
17. CI pipeline (lint → compile → migrate → test → eval → docker)
18. GitHub Actions deploy workflow (SSH → ECS → compose up → smoke test)
19. Smoke test script
20. Bootstrap tenant script

---

## 3. CURRENT BROKEN FEATURES / CRITICAL BUGS

### CRITICAL (blocks production)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| B1 | **Vector dimension mismatch** | Model: `Vector(1024)`, Migration 0001: `Vector(dim=1536)`, Workers AI: 1024-dim | Runtime crash on embedding insertion — DB column expects 1536 but code sends 1024 |
| B2 | **Production compose missing frontend** | `docker-compose.prod.yml` | Startup crash — `StaticFiles(directory="/app/frontend")` but directory not mounted or COPY'd in Dockerfile |
| B3 | **Production compose missing nginx** | `docker-compose.prod.yml` | Deployment manual references nginx commands but no nginx service defined |
| B4 | **Bank transfer route model mismatches** | `payments.py` bank_router | References `Order.user_id` (doesn't exist), `Payment.method` (doesn't exist), `order.total_amount` (doesn't exist), missing datetime import — will crash at runtime |
| B5 | **Invoice creation bug** | `commerce.py` create_invoice() | Does `db.add(order)` instead of `db.add(invoice)`, then `db.refresh(invoice)` fails |
| B6 | **Frontend exposes provisioning token** | `frontend/index.html` | Hardcoded `PROVISION_TOKEN = 'change-tenant-provisioning-token'` in client-side JS — anyone can create tenants |

### HIGH (security/compliance)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| S1 | No PostgreSQL RLS | All queries | Tenant isolation is application-level only — a bug in any route could leak cross-tenant data |
| S2 | No rate limiting on auth routes | `auth.py` | Brute-force login risk |
| S3 | `.env.prod` was committed to git | Git history | Real secrets in history (now removed from tracking, but still in commit history) |

### MEDIUM (UX/quality)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| M1 | Frontend is single-file vanilla HTML/JS | `frontend/index.html` | No framework, no build step, no component reuse, no routing, no state management |
| M2 | No marketing website | — | Only an admin-style SPA exists; no landing page, no SEO, no brand presence |
| M3 | No mobile responsive design | Frontend | Dark admin theme, not designed for mobile |
| M4 | No streaming for AI responses | Reports route | Synchronous request/response — no real-time feedback during report generation |
| M5 | Empty `docs/product/requirements/` | Docs | No actual PRDs written |

---

## 4. OLD FRONTEND ASSETS FOUND

**Git history:** None — project was delivered as plain files, no git repo existed.

**Two frontend versions found:**

| Version | Location | Size | Description |
|---------|----------|------|-------------|
| V1 (older) | `/Users/shajindi/Desktop/部署/yance-ai-deploy-v0.1.0/frontend/index.html` | 16,932 bytes / 333 lines | English admin panel, dark theme (#0a0a0f + purple #6c5ce7), hardcoded localhost:8001 |
| V2 (current) | `/Users/shajindi/Desktop/部署/yance-ai/frontend/index.html` | 26,664 bytes / 548 lines | Chinese customer-facing SaaS, same dark/purple theme, relative API paths, payment flow |

**Conclusion:** No "beautiful" marketing website version exists. Both are functional admin interfaces. The original v0.1.0 delivery (zip) had NO frontend at all. The frontend was built ad-hoc on deployment day.

**Other copies:**
- `/Users/shajindi/Desktop/部署/yance-ai 2/` — duplicate of initial delivery, no frontend
- `/Users/shajindi/Desktop/部署/yance-ai-deploy-v0.1.0.zip` — original zip, no frontend inside

---

## 5. DESIGN BENCHMARK

**Full document:** `docs/DESIGN_BENCHMARK.md` (812 lines, 26 sites analyzed)

### Top 10 Design Principles (synthesized from Harvey, Sierra, Glean, Hebbia, Cursor, Vercel, Linear, Attio, Clay, etc.)

1. **One headline, one promise** — ≤8-word declarative headline + one-sentence who/why
2. **Proof before product** — Logo wall + stats appear before product detail
3. **Numbers as primary trust language** — Specific metrics (hours saved, %, $, latency) beat adjectives
4. **Simulated product UI > static screenshots** — Content-filled UI vignettes, not raw screenshots or abstract art
5. **Dual-track conversion** — Self-serve + sales coexist
6. **IA organized by customer job, not org chart** — Nav groups follow verbs and workflows
7. **Compliance as first-class content** — SOC 2, ISO 27001, ISO 42001 as homepage content
8. **Restraint in color; identity in type** — Neutral surfaces + one accent + custom/branded fonts
9. **Human oversight is a stated design value** — Trust copy promises supervision at every autonomy claim
10. **The prompt box is becoming the hero** — AI interaction itself above the fold

### Yance Visual Direction (proposed)

**Reference axis:** Harvey × Sierra × Linear × Vercel × Phia

**Palette:** Light-bone base (warm white `#FAFAF8` or similar) + charcoal text + one accent (Yance blue `#0066CC` from brand guidelines, used sparingly ≤10% of pixels)

**Typography:** Distinctive pairing — display grotesk or refined sans for headlines + mono for data/precision signals. Consider: Inter/Geist for UI, JetBrains Mono or similar for data.

**Grid:** 12-column, max-width 1280px, generous whitespace, hairline dividers optional

**Motion budget:** One signature motion (subtle hero animation or simulated agent workflow) + scroll/hover states. No decorative excess.

**AI-native signals:** Show agent workflow, tool-call traces, policy evidence cards, eligibility check visualization. Prompt box as hero interaction.

---

## 6. PROPOSED INFORMATION ARCHITECTURE

### A. Marketing Website (yance.ai)

```
/                          → Landing page
/product                   → Product deep-dive
/solutions/[industry]      → Industry solutions (AI, semiconductor, biotech, etc.)
/pricing                   → Pricing tiers
/security                  → Trust & security page
/resources                 → Blog, guides, case studies
/company                   → About, team, contact
/en                        → English version (future)
```

**Landing page sections (13 sections per master task spec):**
1. NAV — Logo / Product / Solutions / Resources / Pricing / Company / Login / Get Started
2. Hero — "中国科技企业成长 Agent" + product UI demo + dual CTA
3. Trusted Intelligence — Logo wall + stats
4. How Yance Works — Company → Opportunities → Eligibility → Roadmap → Execution
5. Enterprise Growth Graph — 8-dimension visualization
6. Opportunity Radar — Policy/Qualification/Funding/Tax/Park/Competition/IP
7. AI Agent — Real agent workflow demonstration
8. Evidence First — Source traceability, policy text, dates, eligibility
9. Growth Roadmap — 30/90/180/365 day timeline
10. Use Cases — AI Startup / Manufacturing / Biotech / Robotics / Semiconductor / New Energy
11. Chrome Extension — Browse → Analyze → Match → Save workflow
12. Pricing — Free / Pro / Enterprise
13. Security / Final CTA / Footer

### B. SaaS Application (app.yance.ai)

```
/login                     → Login
/register                  → Registration
/onboarding                → Company onboarding (5-step wizard)
/dashboard                 → Overview dashboard
/agent                     → Yance Agent (chat interface)
/opportunities             → Opportunity list + detail
/qualifications            → Qualification ladder
/policies                  → Policy library + search
/roadmap                   → Growth roadmap
/projects                  → Project management
/reports                   → Report list + viewer
/reports/:id               → Report detail (structured UI, not markdown)
/documents                 → Document management
/orders                    → Order history
/orders/:id                → Order detail + payment
/settings                  → Company settings + team
```

**Dashboard sidebar:**
Overview / Yance Agent / Opportunities / Qualifications / Policies / Roadmap / Projects / Reports / Documents / Orders / Company / Settings

---

## 7. PROPOSED DESIGN SYSTEM

### Design Tokens

```
Colors:
  --yance-bg:           #FAFAF8 (warm white)
  --yance-bg-subtle:    #F5F5F0
  --yance-bg-muted:     #EBEBE6
  --yance-text:         #1A1A1A
  --yance-text-secondary: #6B6B6B
  --yance-text-tertiary:  #9B9B9B
  --yance-accent:       #0066CC (brand blue)
  --yance-accent-hover: #0052A3
  --yance-success:      #059669
  --yance-warning:      #D97706
  --yance-error:        #DC2626
  --yance-border:       #E5E5E0

Typography:
  --font-display:       'Inter', system-ui, sans-serif
  --font-body:          'Inter', system-ui, sans-serif
  --font-mono:          'JetBrains Mono', 'Fira Code', monospace
  --text-xs:            0.75rem / 12px
  --text-sm:            0.875rem / 14px
  --text-base:          1rem / 16px
  --text-lg:            1.125rem / 18px
  --text-xl:            1.25rem / 20px
  --text-2xl:           1.5rem / 24px
  --text-3xl:           1.875rem / 30px
  --text-4xl:           2.25rem / 36px
  --text-5xl:           clamp(2.5rem, 5vw, 3.5rem) / hero

Spacing (4px base):
  --space-1: 4px    --space-2: 8px    --space-3: 12px
  --space-4: 16px   --space-5: 20px   --space-6: 24px
  --space-8: 32px   --space-10: 40px  --space-12: 48px
  --space-16: 64px  --space-20: 80px  --space-24: 96px

Radius:
  --radius-sm: 4px    --radius-md: 8px    --radius-lg: 12px
  --radius-xl: 16px   --radius-full: 9999px

Shadow:
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05)
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07)
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08)

Breakpoints:
  --bp-sm: 640px    --bp-md: 768px    --bp-lg: 1024px
  --bp-xl: 1280px   --bp-2xl: 1440px

Max-width: 1280px (content), 1440px (full grid)
```

### Component Library (to build)
- Button (primary/secondary/ghost/destructive, 3 sizes)
- Input, Select, Textarea, Checkbox
- Card, Badge, Tag
- Table, DataGrid
- Modal, Drawer, Toast
- Navigation (top nav, sidebar, breadcrumb)
- Agent chat interface (streaming, tool-call display)
- Report viewer (structured sections)
- Data visualization (radar chart for 8-dim profile, timeline for roadmap)
- Empty states, Loading skeletons, Error boundaries

---

## 8. PROPOSED PRODUCTION ARCHITECTURE

### Option A: Tencent Cloud Hong Kong (per master task)

```
Internet
  ↓
Cloudflare (DNS + CDN + WAF + HTTPS)
  ↓
Tencent Cloud Hong Kong (CVM / Lighthouse)
  ↓
Nginx (reverse proxy + HTTPS termination)
  ├── /           → Frontend (static build, Next.js export or Vite SPA)
  ├── /app/*      → Frontend (SaaS application)
  └── /api/*      → FastAPI backend (uvicorn, 4 workers)
        ↓
    Docker Compose
        ├── nginx
        ├── backend (FastAPI)
        ├── postgres (pgvector:pg16)
        └── redis (optional, for caching/rate-limiting)
```

### Option B: Alibaba Cloud (existing plan in 明日部署手册.md)

Same architecture but on Alibaba Cloud ECS + RDS + OSS. The existing deployment documentation targets Alibaba Cloud.

### Recommendation
**Start with Alibaba Cloud** (existing docs, existing OSS setup, existing RAM policies) to minimize migration risk. Can migrate to Tencent Cloud HK later if ICP issues arise.

### Docker Compose (production, target)

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./frontend/dist:/usr/share/nginx/html
      - certbot-etc:/etc/letsencrypt
    depends_on: [backend]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]

  backend:
    build: .
    env_file: .env.prod
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: yance
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: []  # NOT exposed to public
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]

  redis:  # optional
    image: redis:alpine
    restart: unless-stopped
```

---

## 9. FILES TO KEEP (no modification)

| File/Dir | Reason |
|----------|--------|
| `app/core/config.py` | Working config with production validator |
| `app/core/security.py` | Working JWT + password hashing |
| `app/core/db.py` | Working SQLAlchemy setup |
| `app/models/models.py` | Working ORM models (except vector dim fix needed) |
| `app/api/deps.py` | Working RBAC + tenant isolation |
| `app/api/routes/auth.py` | Working auth flow |
| `app/api/routes/health.py` | Working health checks |
| `app/api/routes/companies.py` | Working company CRUD |
| `app/api/routes/policies.py` | Working policy CRUD + search |
| `app/api/routes/reports.py` | Working AI report generation |
| `app/services/llm/` | Working LLM provider abstraction |
| `app/services/vectorstores/` | Working PGVector implementation |
| `app/services/oss.py` | Working Aliyun OSS integration |
| `alembic/` | Working migrations (except vector dim) |
| `Dockerfile` | Working multi-stage build |
| `.github/workflows/ci.yml` | Working CI pipeline |
| `tests/` | Working test suite |
| `evals/` | Working eval framework |
| `scripts/` | Working bootstrap + smoke scripts |

---

## 10. FILES TO MODIFY

| File | Change | Risk |
|------|--------|------|
| `app/models/models.py` | Fix `Vector(1024)` ↔ migration `Vector(dim=1536)` mismatch | Medium — need migration |
| `app/api/routes/commerce.py` | Fix `db.add(order)` → `db.add(invoice)` bug | Low |
| `app/api/routes/payments.py` | Fix bank_router model field references | Low |
| `docker-compose.prod.yml` | Add nginx service, frontend volume mount | Low |
| `Dockerfile` | Add `COPY frontend/ /app/frontend/` (or switch to built frontend) | Low |
| `app/main.py` | Update static files mount for new frontend build output | Low |
| `app/api/router.py` | Add new routes as SaaS features are built | Low |
| `app/services/llm/router.py` | Add Hunyuan, Kimi, GLM providers | Low |
| `nginx/conf.d/default.conf` | Add frontend serving, WebSocket support, security headers | Low |
| `.env.example` | Add new env vars for additional LLM providers | Low |

---

## 11. FILES TO CREATE

### Frontend (new)
| File | Description |
|------|-------------|
| `frontend-marketing/` | New directory for marketing website (Next.js or Astro) |
| `frontend-app/` | New directory for SaaS application (Next.js or React + Vite) |
| `frontend-marketing/package.json` | Dependencies |
| `frontend-marketing/src/app/page.tsx` | Landing page |
| `frontend-app/package.json` | Dependencies |
| `frontend-app/src/app/dashboard/page.tsx` | Dashboard |

### Documentation
| File | Description |
|------|-------------|
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/PRODUCT.md` | Product definition |
| `docs/DESIGN_SYSTEM.md` | Design tokens + component specs |
| `docs/DATABASE.md` | Schema documentation |
| `docs/LLM_GATEWAY.md` | LLM provider abstraction docs |
| `docs/AGENT_ARCHITECTURE.md` | Agent tool architecture |
| `docs/PAYMENTS.md` | Payment flow documentation |
| `docs/DEPLOYMENT.md` | Production deployment guide |
| `docs/SECURITY.md` | Security documentation |
| `docs/CHROME_EXTENSION_PLAN.md` | Chrome extension roadmap |
| `docs/RUNBOOK.md` | Operations runbook |

### Backend (new services)
| File | Description |
|------|-------------|
| `app/services/llm/providers/hunyuan.py` | Tencent Hunyuan provider |
| `app/services/llm/providers/kimi.py` | Kimi (Moonshot) provider |
| `app/services/llm/providers/glm.py` | GLM (Zhipu) provider |
| `app/services/agent/` | Agent architecture (tools, planning, execution) |
| `app/services/payments/` | Payment provider abstraction |

### Infrastructure
| File | Description |
|------|-------------|
| `docker-compose.prod.yml` (update) | Add nginx, redis |
| `nginx/conf.d/app.conf` | SaaS application proxy config |
| `nginx/conf.d/marketing.conf` | Marketing site config |

---

## 12. DATABASE CHANGES

### Required Migration (CRITICAL)

**Vector dimension fix:**
```sql
-- Current: migration 0001 creates Vector(dim=1536)
-- Model: Vector(1024)
-- Workers AI: produces 1024-dim vectors
-- Fix: ALTER TABLE policies ALTER COLUMN embedding TYPE vector(1024)
```

**Migration 0005 (proposed):**
```python
# alembic/versions/20260809_0005_fix_vector_dim.py
def upgrade():
    op.execute("ALTER TABLE policies ALTER COLUMN embedding TYPE vector(1024)")

def downgrade():
    op.execute("ALTER TABLE policies ALTER COLUMN embedding TYPE vector(1536)")
```

### Future Schema Additions (Phase 9+)

| Table | Purpose |
|-------|---------|
| `company_profile_version` | Track profile evolution (progressive profiling) |
| `agent_tool_call` | Agent observability (tool name, input, output, latency) |
| `report_section` | Structured report sections (not just markdown blob) |
| `deadline` | Application deadlines with reminders |
| `project` | User projects (application tracking) |
| `roadmap_item` | Growth roadmap items (30/90/180/365 day) |
| `qualification` | Qualification tracking (专精特新, 高新, etc.) |

---

## 13. API CHANGES

### New Endpoints (Phase 6-8)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Public registration (replaces bootstrap) |
| POST | `/auth/forgot-password` | Password reset |
| POST | `/auth/reset-password` | Password reset confirmation |
| GET | `/company/profile/summary` | Company profile summary for dashboard |
| GET | `/company/growth-score` | Yance Growth Score |
| POST | `/agent/chat` | Agent chat (streaming SSE) |
| GET | `/agent/sessions` | Agent session history |
| GET | `/opportunities/radar` | Opportunity radar view |
| GET | `/qualifications/ladder` | Qualification ladder |
| GET | `/roadmap` | Growth roadmap |
| POST | `/roadmap/generate` | AI-generated roadmap |
| GET | `/reports/:id/sections` | Structured report sections |
| POST | `/deadlines` | Deadline management |
| GET | `/dashboard/overview` | Dashboard overview data |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /reports/generate` | Add streaming (SSE) support |
| `POST /policies/search` | Add metadata filters + rerank |
| `POST /auth/bootstrap` | Deprecate (replace with public register) |
| `POST /auth/provision-tenant` | Restrict to server-side only (remove from frontend) |

---

## 14. SECURITY RISKS

### Critical

| Risk | Current State | Fix |
|------|---------------|-----|
| Provisioning token in frontend | Hardcoded in client JS | Remove from frontend, server-only |
| No PostgreSQL RLS | Application-level only | Add RLS policies as defense-in-depth |
| Secrets in git history | `.env.prod` in first commit | `git filter-branch` or BFG Repo Cleaner |
| Bank transfer route crashes | Model field mismatches | Fix field references |

### High

| Risk | Current State | Fix |
|------|---------------|-----|
| No rate limiting on auth | Open to brute force | Add rate limiting (nginx + middleware) |
| No CSRF protection | — | Add CSRF tokens for state-changing requests |
| Swagger in non-prod only | Good | Keep disabled in production |
| No input validation on some routes | Partial | Add Pydantic validation everywhere |

### Medium

| Risk | Current State | Fix |
|------|---------------|-----|
| No audit log for sensitive operations | AuditLog table exists but not used everywhere | Add audit logging for company/order/payment changes |
| No backup strategy documented | — | Document pg_dump schedule + retention |
| No automated secret rotation | — | Document rotation procedure |

---

## 15. DEPLOYMENT PLAN

### Phase 1: Local Development (Week 1-2)
1. Fix critical bugs (B1-B6)
2. Build new marketing website locally
3. Build new SaaS frontend locally
4. Add LLM providers (Hunyuan, Kimi, GLM)
5. Add agent architecture
6. Test everything locally with Docker Compose dev

### Phase 2: Staging (Week 3)
1. Deploy to staging server (Alibaba Cloud ECS)
2. Run full test suite
3. Visual QA across devices
4. Performance optimization
5. Security audit

### Phase 3: Production (Week 4)
1. DNS cutover: yance.ai → new marketing site
2. DNS cutover: app.yance.ai → new SaaS app
3. api.yance.ai → FastAPI backend
4. Monitor for 48 hours
5. Rollback plan ready

### Rollback Plan
- DNS TTL set to 300s before cutover
- Old backend Docker image tagged and preserved
- Database backup before any schema changes
- Git branch `production-rebuild-v1` preserves all history
- Can revert DNS to old server within 5 minutes

---

## 16. TEST PLAN

### Unit Tests
- [ ] Config validation (existing, passing)
- [ ] Health endpoint (existing, passing)
- [ ] JWT/password roundtrip (existing, passing)
- [ ] Vector dimension consistency (new)
- [ ] Invoice creation fix (new)
- [ ] Bank transfer route (new)
- [ ] LLM provider fallback chain (new)
- [ ] Payment state machine (new)

### Integration Tests
- [ ] Registration → Login → Create company → Dashboard (new)
- [ ] Policy search → Report generation → Order → Payment → Unlock (new)
- [ ] Cross-tenant isolation (existing, expand)
- [ ] Agent tool calls (new)
- [ ] Streaming response (new)

### E2E Tests
- [ ] Full user journey: register → onboard → search → report → pay → view (new)
- [ ] Chrome extension → Web workspace sync (future)
- [ ] Mobile responsive (new)

### Visual QA
- [ ] 1440px Desktop (Chrome, Safari)
- [ ] MacBook (1440px)
- [ ] iPad (768px / 1024px)
- [ ] iPhone (375px / 390px)
- [ ] Check: overflow, fonts, spacing, loading, hover, focus, forms, charts, tables

### Performance
- [ ] Marketing site: LCP < 2.5s, FID < 100ms, CLS < 0.1
- [ ] Dashboard: initial load < 3s, API response < 500ms
- [ ] Agent streaming: first token < 1s
- [ ] Image optimization: WebP/AVIF, lazy loading

---

## Execution Order (Risk-Low to Risk-High)

| Phase | Task | Risk | Est. Time |
|-------|------|------|-----------|
| 0 | ✅ Repo audit | None | Done |
| 1 | ✅ Backup (git init + branch) | None | Done |
| 2 | ✅ Find old frontend | None | Done |
| 3 | ✅ Benchmark research | None | Done |
| 4 | ✅ Read current code | None | Done |
| 5 | Fix B1: Vector dimension migration | Medium | 2h |
| 6 | Fix B2-B3: Docker compose + Dockerfile | Low | 1h |
| 7 | Fix B4-B5: Bank transfer + invoice bugs | Low | 1h |
| 8 | Fix B6: Remove provisioning token from frontend | Low | 30min |
| 9 | Fix S1-S3: Security hardening | Medium | 4h |
| 10 | Build design system (tokens + components) | None | 8h |
| 11 | Build marketing website | Low | 16h |
| 12 | Build SaaS dashboard | Low | 16h |
| 13 | Build agent chat interface | Medium | 12h |
| 14 | Build report viewer (structured) | Low | 8h |
| 15 | Connect new frontend to existing APIs | Low | 8h |
| 16 | Add LLM providers (Hunyuan/Kimi/GLM) | Low | 4h |
| 17 | Add agent architecture (tools) | Medium | 12h |
| 18 | Auth hardening (register/forgot-password) | Low | 4h |
| 19 | Payment hardening (provider abstraction) | Medium | 6h |
| 20 | Production Docker + deployment | Medium | 6h |
| 21 | Visual QA + E2E tests | Low | 8h |
| 22 | Documentation | Low | 4h |

**Total estimated: ~140 hours of focused work**

---

## Definition of Done

- [ ] https://yance.ai — Professional AI SaaS marketing website
- [ ] https://app.yance.ai — Full SaaS flow (register → login → company → dashboard → search → report → order → payment → unlock)
- [ ] AI layer: Qwen working, other providers structurally ready (key = enabled)
- [ ] Production deployment: Tencent Cloud HK or Alibaba Cloud, Mac-independent
- [ ] Database: Persistent, migrated, backed up
- [ ] HTTPS: Working on all subdomains
- [ ] Secrets: Secure, not in git, not in frontend
- [ ] Original business loop: Not broken
- [ ] Deliverables: Change list, git diff, test results, screenshots, deployment architecture, deployment commands, env template, rollback plan, known issues, next sprint suggestions

---

*This document is the single source of truth for the production rebuild. Update as work progresses.*
