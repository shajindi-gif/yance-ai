# Public Claim Register

Last reviewed: 2026-09-03

This register separates code-backed facts from deployment-dependent controls and roadmap
statements. Public copy must not promote a claim to a stronger state without linked evidence.

| Claim area | State | Current evidence | Allowed public wording |
| --- | --- | --- | --- |
| Password storage | Code-backed | `app/core/security.py`; auth tests | Passwords are hashed; do not name a production policy not enforced in code. |
| Authentication expiry | Code-backed | JWT settings and principal dependency | Access tokens expire; do not claim SSO, MFA, or hardened cookie sessions. |
| Tenant and role checks | Code-backed, incomplete defense in depth | `app/api/deps.py`; route filters; security boundary tests | APIs validate active user, tenant, role, and scoped resources. Do not claim database RLS. |
| Payment settlement | Code-backed | payment event ledger, provider validation, replay tests | Price, amount, currency, metadata, and resource ownership are server-validated. Success depends on provider callback settlement. |
| Document upload limits | Code-backed | document routes, OSS size lookup, upload tests | PDF, DOCX, XLSX, CSV, and TXT are accepted up to the configured limit. Do not claim malware scanning. |
| PDF and invoice rendering | Code-backed | escaping and deny-fetch boundary tests | Untrusted values are escaped and renderer network/file fetches are denied. |
| Eligibility hard gates | Code-backed for current rules | deterministic evaluator tests | Known blocking safety, environmental, and credit failures cannot be returned as eligible. Human review remains required. |
| Policy citations | Partial | source fields exist; end-to-end citation coverage is not complete | Results should be checked against displayed sources. Do not claim every conclusion has article-level citation yet. |
| TLS, encryption at rest, backups | Deployment-dependent | no repository proof of a production environment | Must be configured and verified for each environment. |
| Private deployment, SLA, SSO, API keys | Roadmap / contract-dependent | not implemented end to end | Describe only as evaluation or roadmap scope, never as generally available. |
| Browser extension and native clients | Concept / roadmap | non-functional concept pages only | Clearly label `CONCEPT DEMO` or `未发布`; provide no fake download action. |
| Pricing and discounts | Database-backed catalog only | `products` table and commerce routes | Display the live product catalog. Do not publish static subscription discounts as active offers. |
| Customers, partners, revenue, usage, growth | No public verified data | no approved source of truth | Show an empty state or say no data is publicly verifiable. |
| Accuracy, coverage, hallucination rate | Not evaluated yet | no frozen benchmark with production results | Show `No evaluation data yet` / `待评测`; never invent a percentage. |
| Demo companies and outcomes | Demo only | static presentation fixtures | Mark prominently as `DEMO`, `Example`, or `Sample` and state that data is fictional. |

## Promotion rule

A roadmap claim becomes code-backed only after implementation, automated verification, and a
linked release record. A deployment claim additionally requires environment-level evidence. A
customer or performance claim requires an approved, reproducible data source and reporting
window.
