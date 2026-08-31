#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2.1 评分器：对比 Track A(DeepSeek Raw) / Track B(Yance+Same DeepSeek) / Track C(Yance+Qwen)
vs 冻结 Gold，计算 15 项指标 + 头对头对比。只读取输出，不修改任何冻结文件。
缺失 case 的 track 仅对该 track 做部分统计（resume 友好）。
"""
import json, os, re, glob
from collections import defaultdict

V21 = "/Users/shajindi/Desktop/yance-backup/yance/benchmark/results/v21"
V1 = "/Users/shajindi/AI-Workspace/qoder 项目1/benchmark"
RAW = f"{V21}/raw"

ENUM = ("ELIGIBLE", "NOT_ELIGIBLE", "INSUFFICIENT_INFO")


def norm_overall(s):
    if not s:
        return None
    s = str(s).strip()
    if s in ENUM:
        return s
    if "不符合" in s:
        return "NOT_ELIGIBLE"
    if "信息不足" in s:
        return "INSUFFICIENT_INFO"
    if "符合" in s:
        return "ELIGIBLE"
    return s


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def load_gold():
    g = {}
    for o in load_jsonl(f"{V21}/gold_eligibility.jsonl"):
        g[o["scenario_id"]] = o
    return g


def load_pid_map():
    m = {}
    for c in load_jsonl(f"{V1}/benchmark_cases.jsonl"):
        pids = c.get("policy_ids") or []
        if pids:
            m[c["scenario_id"]] = pids[0]
    return m


def load_policies():
    ps = load_jsonl(f"{V1}/policy_library/policies.jsonl")
    out = {}
    for p in ps:
        parts = [f"《{p['policy_name']}》（{p['doc_number']}，{p['issuer']}）"]
        for c in p["clauses"]:
            parts.append(f"【{c['clause_id']}】{c['verbatim_text']}")
        out[p["policy_id"]] = "\n".join(parts)
    return out


def load_track(name):
    """返回 {scenario_id: rec}。Track A 取自 parsed；B/C 取自顶层。"""
    d = f"{RAW}/{name}"
    res = {}
    if not os.path.isdir(d):
        return res
    for fp in glob.glob(f"{d}/*.json"):
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        sid = rec.get("scenario_id")
        if not sid:
            continue
        if "error" in rec and "overall_result" not in rec:
            res[sid] = {"error": rec["error"]}
            continue
        if name.startswith("deepseek_raw"):
            parsed = rec.get("parsed", {})
            overall = norm_overall(parsed.get("overall_result"))
            criteria = parsed.get("criteria", []) if isinstance(parsed, dict) else []
            http = rec.get("http_status")
            res[sid] = {"overall_result": overall, "criteria": criteria,
                        "valid": overall in ENUM and http == 200,
                        "latency_s": rec.get("latency_s"),
                        "meta": {"hallucinations_blocked": 0,
                                 "deterministic_evaluated": 0,
                                 "input_tokens": rec.get("input_tokens"),
                                 "output_tokens": rec.get("output_tokens")}}
        else:
            overall = norm_overall(rec.get("overall_result"))
            criteria = rec.get("criteria", [])
            md = rec.get("model_metadata", {}) or {}
            tel = md.get("telemetry", {}) or {}
            res[sid] = {"overall_result": overall, "criteria": criteria,
                        "valid": overall in ENUM,
                        "latency_s": (md.get("latency_ms") or 0) / 1000.0,
                        "meta": {"hallucinations_blocked": md.get("hallucinations_blocked", 0),
                                 "deterministic_evaluated": md.get("deterministic_evaluated", 0),
                                 "validation_failure_count": tel.get("validation_failure_count", 0),
                                 "input_tokens": tel.get("input_tokens"),
                                 "output_tokens": tel.get("output_tokens")}}
    return res


POLICY_NUM_RE = re.compile(r"\d+(?:\.\d+)?(?:%|％|万|亿|年|个月|天|人|项|件|分)")


def policy_numbers(text):
    return set(POLICY_NUM_RE.findall(text or ""))


def criterion_evidence(c):
    return (c.get("evidence_quote") or c.get("evidence") or "").strip()


def criterion_policy_ref(c):
    """模型引用的『政策原文』字段（不含企业自身数字）。"""
    return (c.get("evidence_quote") or c.get("policy_requirement") or c.get("evidence") or "")


def scan_hallucination(criteria, polynums):
    """政策断言幻觉扫描（对齐 V21_AUDIT D2）：
    仅检查模型在【政策引用】字段中给出的比例/金额类数字是否真的出现在政策原文中。
    企业自身计算数字（如 16.7%、480万）一律豁免，不算幻觉。
    返回 True 表示该 case 至少存在 1 处政策断言幻觉。
    """
    for c in criteria:
        ref = criterion_policy_ref(c)
        if not ref:
            continue
        nums = POLICY_NUM_RE.findall(ref)
        for n in nums:
            base = n.rstrip("％%")
            norm = lambda s: s.rstrip("0").rstrip(".")
            if n not in polynums and base not in polynums and norm(base) not in {norm(x) for x in polynums}:
                return True
    return False


def score_track(track, gold, policies, pid_map):
    n = 0
    acc = 0
    hard_gate_tp = hard_gate_fn = 0
    fp = 0  # ELIGIBLE but gold NOT_ELIGIBLE
    fn_insuff = 0  # INSUFFICIENT but gold ELIGIBLE
    valid = 0
    ev_total = ev_has = 0
    halluc_cases = 0
    halluc_blocked_total = 0
    det_total = 0
    lat = []
    gold_ne = gold_el = 0
    by_diff = defaultdict(lambda: [0, 0])  # diff -> [acc, n]
    by_type = defaultdict(lambda: [0, 0])
    errors = []

    for sid in sorted(gold.keys()):
        g = gold[sid]
        rec = track.get(sid)
        if rec is None:
            continue
        if "error" in rec:
            errors.append((sid, rec["error"]))
            continue
        n += 1
        overall = rec["overall_result"]
        if overall in ENUM:
            valid += 1
        gold_v = g["gold_q1"]
        if overall == gold_v:
            acc += 1
            by_diff[g["difficulty"]][0] += 1
            by_type[g["case_type"]][0] += 1
        by_diff[g["difficulty"]][1] += 1
        by_type[g["case_type"]][1] += 1

        # hard gate (gold NOT_ELIGIBLE)
        if gold_v == "NOT_ELIGIBLE":
            gold_ne += 1
            if overall == "NOT_ELIGIBLE":
                hard_gate_tp += 1
            else:
                hard_gate_fn += 1
                if overall == "ELIGIBLE":
                    fp += 1
        if gold_v == "ELIGIBLE":
            gold_el += 1
            if overall == "INSUFFICIENT_INFO":
                fn_insuff += 1

        # evidence grounding
        for c in rec["criteria"]:
            ev_total += 1
            if criterion_evidence(c):
                ev_has += 1
        # hallucination（case 级，去重：gate 拦截 或 政策断言扫描命中 任一即记 1）
        hb = rec["meta"].get("hallucinations_blocked", 0)
        halluc_blocked_total += hb
        scan_flag = scan_hallucination(rec["criteria"], policy_numbers(policies.get(pid_map.get(sid, ""), "")))
        if (hb and hb > 0) or scan_flag:
            halluc_cases += 1
        det_total += rec["meta"].get("deterministic_evaluated", 0)
        if rec.get("latency_s"):
            lat.append(rec["latency_s"])

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else None

    return {
        "track": track_name(track) if False else None,
        "cases_scored": n,
        "errors": errors,
        "eligibility_accuracy_pct": pct(acc, n),
        "hard_gate_recall_pct": pct(hard_gate_tp, gold_ne) if gold_ne else None,
        "false_positive_pct": pct(fp, gold_ne) if gold_ne else 0.0,
        "false_negative_insufficient_pct": pct(fn_insuff, gold_el) if gold_el else 0.0,
        "structured_output_pct": pct(valid, n),
        "evidence_grounding_pct": pct(ev_has, ev_total),
        "hallucination_cases": halluc_cases,
        "hallucination_pct": pct(halluc_cases, n),
        "hallucinations_blocked_by_gate": halluc_blocked_total,
        "deterministic_evaluated_total": det_total,
        "avg_latency_s": round(sum(lat) / len(lat), 2) if lat else None,
        "gold_not_eligible": gold_ne,
        "gold_eligible": gold_el,
        "by_difficulty": {k: {"acc": v[0], "n": v[1], "pct": pct(v[0], v[1])} for k, v in by_diff.items()},
        "by_case_type": {k: {"acc": v[0], "n": v[1], "pct": pct(v[0], v[1])} for k, v in by_type.items()},
    }


def track_name(_):
    return None


def main():
    gold = load_gold()
    policies = load_policies()
    pid_map = load_pid_map()
    tracks = {
        "Track A (DeepSeek Raw)": load_track("deepseek_raw"),
        "Track B (Yance + Same DeepSeek)": load_track("yance_same_model"),
    }
    c = load_track("yance_qwen")
    if c:
        tracks["Track C (Yance + Qwen)"] = c

    stats = {}
    for name, tr in tracks.items():
        s = score_track(tr, gold, policies, pid_map)
        s["track"] = name
        stats[name] = s

    os.makedirs(V21, exist_ok=True)
    with open(f"{V21}/stats_v21.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 控制台摘要
    print(f"Gold: {len(gold)} cases | tracks loaded: {list(tracks.keys())}")
    print(f"{'metric':32} " + "  ".join(f"{name.split(' ')[0]+' '+name.split(' ')[1]}"[:14] for name in tracks))
    rows = [
        ("cases_scored", "cases_scored"),
        ("eligibility_accuracy_pct", "EligAcc%"),
        ("hard_gate_recall_pct", "HardGate%"),
        ("false_positive_pct", "FP%"),
        ("false_negative_insufficient_pct", "FNinsuf%"),
        ("structured_output_pct", "Struct%"),
        ("evidence_grounding_pct", "Evid%"),
        ("hallucination_pct", "Hallu%"),
        ("avg_latency_s", "Lat_s"),
    ]
    for key, label in rows:
        line = f"{label:14} "
        for name in tracks:
            v = stats[name].get(key)
            line += f"{str(v):>14} "
        print(line)
    # 头对头：Yance(same) vs DeepSeek(raw)
    if "Track A (DeepSeek Raw)" in stats and "Track B (Yance + Same DeepSeek)" in stats:
        a = stats["Track A (DeepSeek Raw)"]
        b = stats["Track B (Yance + Same DeepSeek)"]
        print("\nHead-to-head (Yance same-model vs DeepSeek raw):")
        print(f"  Eligibility Accuracy: {b['eligibility_accuracy_pct']}%  vs  {a['eligibility_accuracy_pct']}%")
        print(f"  Hard-Gate Recall:     {b['hard_gate_recall_pct']}%  vs  {a['hard_gate_recall_pct']}%")
        print(f"  False Positive:       {b['false_positive_pct']}%  vs  {a['false_positive_pct']}%")
        print(f"  Evidence Grounding:   {b['evidence_grounding_pct']}%  vs  {a['evidence_grounding_pct']}%")
        print(f"  Hallucination:        {b['hallucination_pct']}%  vs  {a['hallucination_pct']}%")
        delta = (b["eligibility_accuracy_pct"] or 0) - (a["eligibility_accuracy_pct"] or 0)
        print(f"  >>> Yance accuracy delta vs raw DeepSeek: {delta:+.1} pp")
    print("\nSaved stats_v21.json")


if __name__ == "__main__":
    main()
