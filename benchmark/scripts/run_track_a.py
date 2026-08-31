#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track A: DeepSeek Raw Baseline。与 Yance 引擎使用同一 DeepSeek 模型(deepseek-chat)、
同一企业画像、同一政策原文、temperature=0，但不经任何 Yance 系统层。"""
import json, os, time, datetime, urllib.request, urllib.error

ENV_PROD = "/Users/shajindi/Desktop/yance-backup/env.prod"
V1_BENCH = "/Users/shajindi/AI-Workspace/qoder 项目1/benchmark"
OUT = "/Users/shajindi/Desktop/yance-backup/yance/benchmark/results/v21/raw/deepseek_raw"

def env_val(key):
    for line in open(ENV_PROD, encoding="utf-8"):
        line = line.strip()
        if line.startswith(key + "="):
            return line.partition("=")[2].strip().strip('"').strip("'")
    return ""

API_KEY = env_val("DEEPSEEK_API_KEY")
MODEL = "deepseek-chat"  # 与引擎 evaluator.py 相同别名

def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

def load_policies():
    ps = load_jsonl(f"{V1_BENCH}/policy_library/policies.jsonl")
    out = {}
    for p in ps:
        parts = [f"《{p['policy_name']}》（{p['doc_number']}，{p['issuer']}）"]
        for c in p["clauses"]:
            parts.append(f"【{c['clause_id']}】{c['verbatim_text']}")
        out[p["policy_id"]] = "\n".join(parts)
    return out

SYSTEM = (
    "你是政策申报资格判定专家。只依据给定的【企业画像】和【政策原文】判断。"
    "规则：1) 对每一个硬性申报条件给出 result: PASS/FAIL/INSUFFICIENT；"
    "2) overall_result：任一条件 FAIL→NOT_ELIGIBLE；无 FAIL 但有 INSUFFICIENT→INSUFFICIENT_INFO；全部 PASS→ELIGIBLE；"
    "3) 每个条件给出 evidence（政策原文引用）与 reason（含计算过程）；"
    "4) 企业画像中已有的数据必须直接使用，不得因字段命名差异判 INSUFFICIENT；"
    "5) 禁止猜测画像缺失的数据；禁止使用政策原文之外的知识或门槛；"
    "6) 严格输出 JSON。"
)

def chat(system, user, max_tokens=4000, timeout=180):
    payload = {"model": MODEL, "messages": [{"role": "system", "content": system},
               {"role": "user", "content": user}], "max_tokens": max_tokens, "temperature": 0}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"

def main():
    os.makedirs(OUT, exist_ok=True)
    policies = load_policies()
    cases = load_jsonl(f"{V1_BENCH}/benchmark_cases.jsonl")
    for case in cases:
        sid = case["scenario_id"]
        out_path = f"{OUT}/{sid}.json"
        if os.path.exists(out_path):
            continue
        pid = case["policy_ids"][0]
        prof = case["enterprise_profile"]
        user = ("【企业画像】\n" + json.dumps(prof, ensure_ascii=False, indent=1) +
                "\n\n【政策原文】\n" + policies[pid] +
                "\n\n请判定该企业是否符合该政策的申报硬门槛，输出 JSON："
                '{"criteria":[{"criterion":"","enterprise_fact":"","result":"PASS|FAIL|INSUFFICIENT",'
                '"reason":"","evidence":"原文引用"}],"overall_result":"ELIGIBLE|NOT_ELIGIBLE|INSUFFICIENT_INFO","summary":""}')
        t0 = time.time()
        code, resp = chat(SYSTEM, user)
        lat = time.time() - t0
        if code == 200:
            content = resp["choices"][0]["message"]["content"]
            usage = resp.get("usage", {})
            model_version = resp.get("model", MODEL)
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = {"raw": content, "json_parse_error": True}
        else:
            content = f"__HTTP_{code}__"
            usage, model_version, parsed = {}, MODEL, {}
        rec = {
            "scenario_id": sid, "benchmark_case_id": case["benchmark_case_id"],
            "system_name": "DeepSeekRaw", "model": MODEL, "model_version": model_version,
            "temperature": 0, "run_timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "latency_s": round(lat, 2), "http_status": code,
            "input_tokens": usage.get("prompt_tokens", "NOT_AVAILABLE"),
            "output_tokens": usage.get("completion_tokens", "NOT_AVAILABLE"),
            "cached_tokens": usage.get("prompt_cache_hit_tokens", "NOT_AVAILABLE"),
            "raw_response": content, "parsed": parsed,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        print(f"{sid} HTTP {code} {lat:.1f}s", flush=True)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
