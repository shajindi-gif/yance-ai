#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yance Policy Evaluation Engine V2.1 — Benchmark Adapter
从 Benchmark V1 冻结数据集读取 Case，转成引擎请求，直接调用 evaluate_policy()。
不经过 chat 页面，不经过 HTTP/DB 层（排除 DB 与认证噪音，聚焦引擎本体）。
"""
import asyncio
import json
import os
import sys

# 注入 yance-ai 到 path
YANCE_AI = "/Users/shajindi/Desktop/yance-backup/yance/yance-ai"
sys.path.insert(0, YANCE_AI)
os.chdir(YANCE_AI)

# 从 env.prod 注入环境变量（只注入，不打印）
ENV_PROD = "/Users/shajindi/Desktop/yance-backup/env.prod"
for line in open(ENV_PROD, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k = k.strip(); v = v.strip().strip('"').strip("'")
    os.environ.setdefault(k, v)

from app.services.policy_engine.evaluator import evaluate_policy  # noqa: E402

V1_BENCH = "/Users/shajindi/AI-Workspace/qoder 项目1/benchmark"


def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_policies():
    """policy_id -> 拼接后的政策原文（含条款号标注）"""
    ps = load_jsonl(f"{V1_BENCH}/policy_library/policies.jsonl")
    out = {}
    for p in ps:
        parts = [f"《{p['policy_name']}》（{p['doc_number']}，{p['issuer']}）"]
        for c in p["clauses"]:
            parts.append(f"【{c['clause_id']}】{c['verbatim_text']}")
        out[p["policy_id"]] = "\n".join(parts)
    return out, {p["policy_id"]: p["policy_name"] for p in ps}


async def run_engine(case, policies, policies_meta, provider):
    """单个 case 走 Yance 引擎。返回完整结果 dict。"""
    # 取该 case 第一个 policy（V1 每个 case 1-2 个 policy，多政策场景只取主政策）
    pid = case["policy_ids"][0]
    policy_content = policies[pid]
    prof = case["enterprise_profile"]
    company_name = prof.get("company_name", "未命名企业")
    result = await evaluate_policy(
        policy_id=pid,
        policy_title=policies_meta.get(pid, pid),
        policy_content=policy_content,
        policy_level="国家级",
        company_name=company_name,
        company_profile=prof,
        provider=provider,
    )
    return result.model_dump()


def main():
    provider = sys.argv[1] if len(sys.argv) > 1 else "deepseek"
    out_dir = f"/Users/shajindi/Desktop/yance-backup/yance/benchmark/results/v21/raw/yance_same_model"
    if provider != "deepseek":
        out_dir = out_dir.replace("yance_same_model", f"yance_{provider}")
    os.makedirs(out_dir, exist_ok=True)

    cases = load_jsonl(f"{V1_BENCH}/benchmark_cases.jsonl")
    policies, policies_meta = load_policies()

    for case in cases:
        sid = case["scenario_id"]
        out_path = f"{out_dir}/{sid}.json"
        if os.path.exists(out_path):
            print(f"skip {sid}")
            continue
        try:
            res = asyncio.run(run_engine(case, policies, policies_meta, provider))
            rec = {
                "scenario_id": sid,
                "benchmark_case_id": case["benchmark_case_id"],
                "provider": provider,
                "overall_result": res["overall_result"],
                "criteria_count": len(res.get("criteria", [])),
                "evidence_count": len(res.get("evidence", [])),
                "hard_failures": res.get("hard_failures", []),
                "missing_information": res.get("missing_information", []),
                "model_metadata": res.get("model_metadata", {}),
                "criteria": res.get("criteria", []),
                "full": res,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            print(f"done {sid} -> {res['overall_result']} (crit={len(res.get('criteria',[]))})")
        except Exception as e:
            print(f"ERROR {sid}: {type(e).__name__}: {str(e)[:200]}")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"scenario_id": sid, "error": f"{type(e).__name__}: {str(e)[:300]}"}, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
