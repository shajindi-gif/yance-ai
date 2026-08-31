#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单例探针：用真实 API 跑 S01（Yance 引擎路径 + Track A 裸 DeepSeek 路径），
确认 (a) 网络/Key 可用 (b) _loads_json 能处理真实 DeepSeek ```json 输出 (c) 当前是否仍 429 限流。
只跑 1 个 case，不污染正式结果目录（写入 probe/ 子目录）。"""
import os, sys, json, asyncio, time, datetime, urllib.request, urllib.error
ENV_PROD = "/Users/shajindi/Desktop/yance-backup/env.prod"
YANCE_AI = "/Users/shajindi/Desktop/yance-backup/yance/yance-ai"
V1_BENCH = "/Users/shajindi/AI-Workspace/qoder 项目1/benchmark"
OUT = "/Users/shajindi/Desktop/yance-backup/yance/benchmark/results/v21/probe"
os.makedirs(OUT, exist_ok=True)
for line in open(ENV_PROD, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
sys.path.insert(0, YANCE_AI)
os.chdir(YANCE_AI)

def env_val(key):
    for line in open(ENV_PROD, encoding="utf-8"):
        line = line.strip()
        if line.startswith(key + "="):
            return line.partition("=")[2].strip().strip('"').strip("'")
    return ""

def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def load_policies():
    ps = load_jsonl(f"{V1_BENCH}/policy_library/policies.jsonl")
    out = {}
    for p in ps:
        parts = [f"《{p['policy_name']}》（{p['doc_number']}，{p['issuer']}）"]
        for c in p["clauses"]:
            parts.append(f"【{c['clause_id']}】{c['verbatim_text']}")
        out[p["policy_id"]] = "\n".join(parts)
    return out, {p["policy_id"]: p["policy_name"] for p in ps}

cases = load_jsonl(f"{V1_BENCH}/benchmark_cases.jsonl")
case = next(c for c in cases if c["scenario_id"] == "S01")
policies, pmeta = load_policies()
pid = case["policy_ids"][0]
prof = case["enterprise_profile"]

# —— Track A 裸 DeepSeek ——
API_KEY = env_val("DEEPSEEK_API_KEY")
SYSTEM = ("你是政策申报资格判定专家。只依据【企业画像】和【政策原文】判断。对每条件给 result: PASS/FAIL/INSUFFICIENT；"
          "overall_result：任一FAIL→NOT_ELIGIBLE；有INSUFFICIENT→INSUFFICIENT_INFO；全PASS→ELIGIBLE。严格输出JSON。")
user = ("【企业画像】\n" + json.dumps(prof, ensure_ascii=False, indent=1) +
        "\n\n【政策原文】\n" + policies[pid] +
        '\n\n输出JSON：{"criteria":[{"criterion":"","result":"PASS|FAIL|INSUFFICIENT","reason":""}],'
        '"overall_result":"ELIGIBLE|NOT_ELIGIBLE|INSUFFICIENT_INFO","summary":""}')
t0 = time.time()
try:
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps({"model": "deepseek-chat", "messages": [{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": user}], "max_tokens": 4000, "temperature": 0}).encode(),
        method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read().decode())
    code = 200
    content = resp["choices"][0]["message"]["content"]
    print(f"[TrackA] HTTP 200  {time.time()-t0:.1f}s")
    print("  raw head:", content[:160].replace("\n", " "))
    try:
        json.loads(content)
        print("  TrackA JSON parses cleanly")
    except Exception:
        print("  TrackA raw is codeblock-wrapped -> needs _loads_json")
except urllib.error.HTTPError as e:
    code = e.code
    print(f"[TrackA] HTTP {code}  {time.time()-t0:.1f}s  body={e.read().decode(errors='replace')[:200]}")
except Exception as e:
    print(f"[TrackA] ERR {type(e).__name__}: {e}")

# —— Yance 引擎路径 ——
print("\n--- Yance engine path (S01) ---")
try:
    from app.services.policy_engine.evaluator import evaluate_policy
    t0 = time.time()
    res = asyncio.run(evaluate_policy(
        policy_id=pid, policy_title=pmeta.get(pid, pid), policy_content=policies[pid],
        policy_level="国家级", company_name=prof.get("company_name", "S01"),
        company_profile=prof, provider="deepseek"))
    md = res.model_metadata
    print(f"[Yance] done {time.time()-t0:.1f}s overall={res.overall_result.value}")
    print(f"  criteria={len(res.criteria)} deterministic={md.get('deterministic_evaluated')} "
          f"halluc_blocked={md.get('hallucinations_blocked')} llm_calls={md.get('telemetry',{}).get('llm_call_count')}")
    print(f"  det_results: " + ", ".join(
        f"{c.criterion[:18]}:{c.result.value}" for c in res.criteria))
    with open(f"{OUT}/S01_yance_probe.json", "w", encoding="utf-8") as f:
        json.dump(res.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"  saved probe/S01_yance_probe.json")
except Exception as e:
    print(f"[Yance] ERR {type(e).__name__}: {str(e)[:300]}")
