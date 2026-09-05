# Yance.ai Investor Demo Script

All presenters must begin with: **“The companies and policies in this environment are explicitly synthetic DEMO data. They are not customers, government partners, revenue, accuracy claims, or submission outcomes.”**

## 3-minute product version

**0:00–0:25 — Positioning**  
Open `/demo`. Say: “Yance turns a persistent company context into an evidence-backed execution workspace. It is not another chat interface.” Point to the synthetic-data boundary.

**0:25–0:55 — Company intelligence**  
Choose the AI software scenario. Show the structured profile and imported-document status. Explain that scans pin an immutable profile version.

**0:55–1:25 — Opportunity and eligibility**  
Advance to Policy Scan and Eligibility. Show Match Score, the four-state result `Potentially Eligible`, structured criteria, confidence and the missing invoice. Emphasize that missing evidence produces a bounded state, not an invented answer.

**1:25–1:55 — Evidence**  
Open Evidence. Point to policy version, article, exact quote, dates, region, source and `Exact span verified`. State that this policy is tenant-private synthetic text with an `.invalid` URL.

**1:55–2:30 — Execution workspace**  
Open Application. Show required documents, hard gate, task progress and Next Best Action. Explain that the opportunity has become persistent work, not a disposable response.

**2:30–3:00 — Deliverable and moat**  
Open Deliverable, show the six-step Agent Run, checksum and version, then download DOCX. Close with: “The moat is the linked company context, policy structure, evidence lineage, workflow state, evaluation and execution history.”

## 7-minute commercial version

Use the 3-minute path, then add:

**3:00–4:00 — Failure-safe behavior**  
Switch to the biomed scenario. Show `Need More Information` and two missing inputs. Explain why Yance does not force every lead into an eligible result.

**4:00–5:00 — Reusable vertical infrastructure**  
Switch between manufacturing, technology services and startup scenarios. Show the same workflow contract with different structured rules, required materials and Next Best Actions.

**5:00–6:00 — Operations and quality**  
In an authenticated admin session, open `/agents/{runId}` and `/admin/evals`. Show stored plan/retrieve/reason/act/verify/finish steps. If no reviewed eval data exists, point out the explicit empty state; do not quote a percentage.

**6:00–7:00 — Business truth**  
Open `/admin/investor-metrics`. Explain that every metric is database-derived and demo tenants are excluded. Only discuss paying customers or revenue if non-zero real records are visible at presentation time.

## 15-minute technical diligence version

**0:00–3:00 — Complete product loop**  
Run the 3-minute version without skipping the evidence or download.

**3:00–5:00 — Data lineage**  
Trace `CompanyProfileVersion → PolicyScan → Opportunity → EligibilityResult → Evidence → ApplicationArtifact`. Explain immutable source versions, exact character spans and artifact checksums.

**5:00–7:00 — Agent harness**  
Show Agent Run status, model/provider, token/cost/latency fields, tool calls, verification, errors and bounded retries. Clarify that the public demo is deterministic and records zero LLM tokens/cost.

**7:00–9:00 — RAG and policy layer**  
Explain metadata filters, full-text + vector retrieval, rank fusion, policy versions/chunks, structured eligibility rules, required materials and benefits. Do not claim a learned reranker.

**9:00–11:00 — Multi-tenancy and security**  
Show tenant ownership, RBAC, private-policy visibility, API-key hashing, audit logs and demo isolation. State current limits: no RLS, SSO/SAML, external pen-test or certification claim yet.

**11:00–12:30 — Evaluation**  
Show five eval families, dataset version/hash/review state, case scores and release gates. Use only reviewed, non-demo persisted results. An empty state is an acceptable, truthful result.

**12:30–14:00 — Deployment and operations**  
Show the CI gate, migrations, separate API/worker processes, structured request IDs and container build. State that repository deployability is not proof of an SLA or live deployment.

**14:00–15:00 — Roadmap and defensibility**  
Close on evidence quality, proprietary workflow state, organization knowledge, evaluation data and execution history. Review [`docs/data-room/TECHNICAL_ROADMAP.md`](docs/data-room/TECHNICAL_ROADMAP.md) and invite diligence on the remaining risks.

## Pre-demo checklist

- Database migration is at head and the safe demo seeder reports five scenarios.
- Run `npm run test:e2e` against the intended local/staging API before a live session; retain failure evidence if it does not pass.
- Run the backend `pytest -m e2e --no-cov` gate against an isolated PostgreSQL database.
- `/demo` shows the synthetic-data notice and all five company types.
- Every scenario completes all seven UI steps.
- Evidence link uses `example.invalid` and the quote is marked verified.
- DOCX download opens; PDF/XLSX/JSON endpoints are healthy.
- Investor metrics exclude demo tenants; no fake commerce or analytics events exist.
- Never improvise customer, revenue, government, accuracy, funding or success claims.

## Verified release-candidate evidence

On 2026-09-06, the Chromium demo gate completed all seven stages and downloaded a DOCX against local Next.js, FastAPI and PostgreSQL services. The backend golden journey passed twice consecutively. These checks prove workflow wiring and repeatability; they do not prove production availability, policy accuracy or customer adoption.
