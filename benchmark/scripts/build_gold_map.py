#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从冻结 gold_answer 生成 gold_eligibility 映射（只读，不修改原 gold）。
取 Q1.standard_judgment 的【首词判定】作为该 case 的整体资格金标准。
映射：符合→ELIGIBLE / 不符合→NOT_ELIGIBLE / 信息不足→INSUFFICIENT_INFO。
对带括号说明的判定（如「符合（指标层面达标）」）取首词。
"""
import json, re, os
V1 = "/Users/shajindi/AI-Workspace/qoder 项目1/benchmark"
OUT = "/Users/shajindi/Desktop/yance-backup/yance/benchmark/results/v21/gold_eligibility.jsonl"
MAP = {"符合": "ELIGIBLE", "不符合": "NOT_ELIGIBLE", "信息不足": "INSUFFICIENT_INFO"}

cases = [json.loads(l) for l in open(f"{V1}/benchmark_cases.jsonl", encoding="utf-8") if l.strip()]
out = []
for c in cases:
    ga = c["gold_answer"]
    q1 = ga.get("Q1", {}).get("standard_judgment", "") or ""
    q2 = ga.get("Q2", {}).get("standard_judgment", "") or ""
    m1 = re.match(r"\s*(符合|不符合|信息不足)", q1)
    m2 = re.match(r"\s*(符合|不符合|信息不足)", q2)
    out.append({
        "scenario_id": c["scenario_id"], "case_type": c["case_type"],
        "difficulty": c["difficulty"],
        "gold_q1": MAP.get(m1.group(1), "?") if m1 else "?",
        "gold_q1_raw": q1[:120],
        "gold_q2": MAP.get(m2.group(1), "?") if m2 else "?",
        "gold_q2_raw": q2[:120],
    })
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")
print("scenario | case_type | gold_q1 -> mapped | gold_q2 -> mapped")
for o in out:
    print(f"  {o['scenario_id']} {o['case_type']:6} Q1={o['gold_q1']:14} ({o['gold_q1_raw'][:24]})  Q2={o['gold_q2']}")
n_unmapped = sum(1 for o in out if o["gold_q1"] == "?")
print(f"\nSaved {len(out)} rows; unmapped Q1 = {n_unmapped}")
