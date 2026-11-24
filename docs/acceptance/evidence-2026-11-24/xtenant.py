"""Cross-tenant IDOR fuzzer: fresh tenant A probes every parametrised route with foreign IDs."""
import re, sys, uuid, warnings, json
warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.db import SessionLocal

PARAM_TABLES = {
 "application_id":["applications"], "company_id":["companies"], "task_id":["tasks","workflow_runs","agent_runs"],
 "invoice_id":["invoices"], "run_id":["agent_runs","workflow_runs","eval_runs"], "document_id":["documents"],
 "tenant_id":["tenants"], "artifact_id":["application_artifacts","artifacts","deliverables"],
 "policy_id":["policies"], "opportunity_id":["opportunities"], "milestone_id":["milestones"],
 "scan_id":["policy_scans"], "requirement_id":["application_requirements"],
 "request_id":["deletion_requests","revision_requests"], "payment_id":["payments"], "order_id":["orders"],
 "notification_id":["notifications"], "key_id":["api_keys"], "job_id":["export_jobs"], "feedback_id":["feedback"],
}
client = TestClient(app)
email = f"xt-{uuid.uuid4().hex}@example.com"
r = client.post("/api/v1/auth/register", json={"company_name":"越权探测租户A","owner_email":email,"owner_name":"探测者A","owner_password":"audit-password-123456","agreed_terms_version":"test-terms"})
assert r.status_code == 201, r.text
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
me = client.get("/api/v1/auth/me", headers=H).json()
A = str(me.get("tenant_id") or me.get("tenant", {}).get("id"))
print("tenant A", A, "role", me.get("role"))

db = SessionLocal()
def cols(t):
    return [c for (c,) in db.execute(text("select column_name from information_schema.columns where table_name=:t"),{"t":t})]
def foreign_rows(t, n=4):
    cs = cols(t)
    where = "where tenant_id::text <> :a" if "tenant_id" in cs else ("where id::text <> :a" if t=="tenants" else "")
    if t=="policies": where += " and tenant_id is not null"   # global policies are legitimately shared
    q = f"select * from {t} {where} order by random() limit {n}"
    return [dict(r._mapping) for r in db.execute(text(q),{"a":A})]

routes = [l.rstrip("\n").split("\t") for l in open(sys.argv[1])]
hits, inconclusive, tested = [], [], 0
for path, methods, auth, mod in routes:
    params = re.findall(r"\{(\w+)\}", path)
    if auth=="PUBLIC" or auth=="platform_admin" or not params: continue
    if any(p not in PARAM_TABLES for p in params): continue
    # leaf param = last one; derive parents from the leaf row's columns
    leaf = params[-1]
    for table in PARAM_TABLES[leaf]:
        for row in foreign_rows(table):
            vals = {leaf: str(row["id"])}
            ok = True
            for p in params[:-1]:
                if p in row and row[p]: vals[p]=str(row[p])
                elif p=="tenant_id" and row.get("tenant_id"): vals[p]=str(row["tenant_id"])
                else: ok=False
            if not ok: continue
            url = path
            for k,v in vals.items(): url = url.replace("{"+k+"}", v)
            for m in methods.split(","):
                if m in ("HEAD","OPTIONS"): continue
                tested += 1
                kw = {} if m in ("GET","DELETE") else {"json":{}}
                resp = client.request(m, url, headers=H, **kw)
                rec = (m, path, table, resp.status_code, resp.text[:160])
                if 200 <= resp.status_code < 300: hits.append(rec)
                elif resp.status_code in (400,422,409,500): inconclusive.append(rec)
print("requests", tested)
print("== 2xx ON FOREIGN IDS"); [print(*h, sep=" | ") for h in hits]
print("== inconclusive (validation/conflict/5xx before or instead of ownership)")
seen=set()
for h in inconclusive:
    if (h[0],h[1],h[3]) in seen: continue
    seen.add((h[0],h[1],h[3])); print(*h, sep=" | ")
