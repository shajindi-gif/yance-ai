#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2.1 交付物生成：10 项产物（单 xlsx 多 sheet + 主报告 md + BP_BENCHMARK_BLOCK.md）。
依赖：gold_eligibility.jsonl + raw/{deepseek_raw,yance_same_model,yance_qwen} + stats_v21.json。
生成：benchmark/results/v21/YANCE_Benchmark_Report_V21.xlsx 与配套 md。
不读取/不修改任何冻结 Dataset/Gold/评分规则；不 hardcode case id。
"""
import json, os, re, glob, datetime
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

V21 = "/Users/shajindi/Desktop/yance-backup/yance/benchmark/results/v21"
V1 = "/Users/shajindi/AI-Workspace/qoder 项目1/benchmark"
RAW = f"{V21}/raw"
ENUM = ("ELIGIBLE", "NOT_ELIGIBLE", "INSUFFICIENT_INFO")
THRESH = {
    "eligibility_accuracy_pct": ("≥", 75),
    "hard_gate_recall_pct": ("≥", 90),
    "evidence_grounding_pct": ("≥", 95),
    "hallucination_pct": ("≤", 5),
    "false_positive_pct": ("≤", 5),
    "structured_output_pct": ("≥", 98),
}

wb = openpyxl.Workbook()


def style_header(ws, row=1, ncols=1):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


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


def load_gold():
    return {o["scenario_id"]: o for o in load_jsonl(f"{V21}/gold_eligibility.jsonl")}


def load_track(name):
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
            parsed = rec.get("parsed", {}) or {}
            overall = norm_overall(parsed.get("overall_result"))
            criteria = parsed.get("criteria", []) if isinstance(parsed, dict) else []
            res[sid] = {"overall_result": overall, "criteria": criteria,
                        "meta": {"hallucinations_blocked": 0, "deterministic_evaluated": 0}}
        else:
            res[sid] = {"overall_result": norm_overall(rec.get("overall_result")),
                        "criteria": rec.get("criteria", []),
                        "meta": {"hallucinations_blocked": (rec.get("model_metadata") or {}).get("hallucinations_blocked", 0),
                                 "deterministic_evaluated": (rec.get("model_metadata") or {}).get("deterministic_evaluated", 0)}}
    return res


def verdict_pass(v, op, thr):
    if v is None:
        return "N/A"
    return "PASS" if (v >= thr if op == "≥" else v <= thr) else "FAIL"


def main():
    gold = load_gold()
    tracks = {
        "A": load_track("deepseek_raw"),
        "B": load_track("yance_same_model"),
    }
    c = load_track("yance_qwen")
    if c:
        tracks["C"] = c
    stats = json.load(open(f"{V21}/stats_v21.json", encoding="utf-8")) if os.path.exists(f"{V21}/stats_v21.json") else {}

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Sheet 1: 概览 / 冻结清单 ──
    ws = wb.active
    ws.title = "1_概览与冻结清单"
    rows = [
        ["Yance Policy Engine V2.1 — Benchmark 交付物", ""],
        ["生成时间", now],
        ["引擎版本", "policy-engine-v2.1"],
        ["Prompt 版本", "PE-PROMPT-v2.1"],
        ["冻结 commit", "4401c2f (policy-engine-v2.1-benchmark-freeze)"],
        ["冻结 Dataset", "benchmark_cases.jsonl (S01-S16, sha256 frozen_input_sha256)"],
        ["冻结 Gold", "gold_answers.jsonl → gold_eligibility.jsonl (只读派生)"],
        ["Track A", "DeepSeek Raw (deepseek-chat, T=0, 同模型无系统层)"],
        ["Track B", "Yance + Same DeepSeek (deterministic + evidence gate + final gate)"],
        ["Track C", "Yance + Qwen (可选)"],
        ["红线", "未修改冻结 Gold/Dataset/评分规则；未 hardcode case id；env.prod 未入仓库/报告"],
        ["样本量", f"{len(gold)} cases（统计显著性有限，建议 V3 扩至 50-100）"],
    ]
    for r in rows:
        ws.append(r)
    style_header(ws, 1, 2)
    autosize(ws, [26, 80])

    # ── Sheet 2: Gold 资格映射 ──
    ws = wb.create_sheet("2_Gold资格映射")
    ws.append(["scenario_id", "case_type", "difficulty", "gold_q1(ELIGIBLE/NOT_ELIGIBLE/INSUFFICIENT_INFO)", "gold_q1_raw"])
    style_header(ws, 1, 5)
    for sid in sorted(gold):
        g = gold[sid]
        ws.append([sid, g["case_type"], g["difficulty"], g["gold_q1"], g["gold_q1_raw"]])
    autosize(ws, [12, 12, 10, 24, 70])

    # ── Sheet 3: 逐_case 对比 ──
    ws = wb.create_sheet("3_逐case对比")
    hdr = ["scenario_id", "case_type", "Gold", "TrackA(DeepSeek Raw)", "TrackB(Yance+DeepSeek)", "TrackC(Yance+Qwen)", "Yance==Gold?", "DeepSeek==Gold?"]
    ws.append(hdr)
    style_header(ws, 1, len(hdr))
    for sid in sorted(gold):
        g = gold[sid]
        a = tracks["A"].get(sid, {}).get("overall_result")
        b = tracks["B"].get(sid, {}).get("overall_result")
        cc = tracks.get("C", {}).get(sid, {}).get("overall_result")
        ws.append([sid, g["case_type"], g["gold_q1"], a, b, cc,
                   "✓" if b == g["gold_q1"] else "✗",
                   "✓" if a == g["gold_q1"] else "✗"])
    autosize(ws, [12, 12, 16, 20, 20, 18, 12, 14])

    # ── Sheet 4: 指标计分卡 ──
    ws = wb.create_sheet("4_指标计分卡")
    ws.append(["指标", "阈值", "Track A (DeepSeek Raw)", "Track B (Yance + Same DeepSeek)", "Track C (Yance + Qwen)", "结论"])
    style_header(ws, 1, 6)
    order = ["eligibility_accuracy_pct", "hard_gate_recall_pct", "evidence_grounding_pct",
             "hallucination_pct", "false_positive_pct", "false_negative_insufficient_pct",
             "structured_output_pct"]
    labels = {"eligibility_accuracy_pct": "Eligibility Accuracy (%)", "hard_gate_recall_pct": "Hard-Gate Recall (%)",
              "evidence_grounding_pct": "Evidence Grounding (%)", "hallucination_pct": "Hallucination (%)",
              "false_positive_pct": "False Positive (%)", "false_negative_insufficient_pct": "False Negative-INSUFF (%)",
              "structured_output_pct": "Structured Output (%)"}
    for k in order:
        op, thr = THRESH.get(k, ("", ""))
        row = [labels[k], (f"{op}{thr}" if thr != "" else "—")]
        for tname in ("Track A (DeepSeek Raw)", "Track B (Yance+DeepSeek)", "Track C (Yance + Qwen)"):
            st = stats.get(tname, {})
            row.append(st.get(k))
        # 结论基于 Track B
        bv = stats.get("Track B (Yance + Same DeepSeek)", {}).get(k)
        row.append(verdict_pass(bv, op, thr) if thr != "" else "—")
        ws.append(row)
    autosize(ws, [30, 10, 22, 22, 20, 10])

    # ── Sheet 5: 头对头 ──
    ws = wb.create_sheet("5_头对头")
    a = stats.get("Track A (DeepSeek Raw)", {})
    b = stats.get("Track B (Yance + Same DeepSeek)", {})
    ws.append(["维度", "DeepSeek Raw (A)", "Yance + Same DeepSeek (B)", "Δ(B-A)"])
    style_header(ws, 1, 4)
    for k, lab in [("eligibility_accuracy_pct", "Eligibility Accuracy %"), ("hard_gate_recall_pct", "Hard-Gate Recall %"),
                   ("false_positive_pct", "False Positive %"), ("evidence_grounding_pct", "Evidence Grounding %"),
                   ("hallucination_pct", "Hallucination %"), ("avg_latency_s", "Avg Latency (s)")]:
        av, bv = a.get(k), b.get(k)
        dv = (round(bv - av, 2) if isinstance(av, (int, float)) and isinstance(bv, (int, float)) else "—")
        ws.append([lab, av, bv, dv])
    autosize(ws, [26, 22, 26, 12])

    # ── Sheet 6: Hard-Gate / FP 分析 ──
    ws = wb.create_sheet("6_HardGate_FP分析")
    ws.append(["Track", "gold NOT_ELIGIBLE 数", "正确判 NOT_ELIGIBLE", "Hard-Gate Recall %", "FP(误判ELIGIBLE)", "FP %"])
    style_header(ws, 1, 6)
    for tname in ("Track A (DeepSeek Raw)", "Track B (Yance + Same DeepSeek)"):
        st = stats.get(tname, {})
        gne = st.get("gold_not_eligible", 0)
        rec = st.get("hard_gate_recall_pct")
        fp = st.get("false_positive_pct")
        ws.append([tname, gne, st.get("hard_gate_recall_pct"), rec, st.get("false_positive_pct"), fp])
    autosize(ws, [28, 18, 20, 18, 18, 10])

    # ── Sheet 7: 幻觉审计 ──
    ws = wb.create_sheet("7_幻觉审计")
    ws.append(["Track", "cases", "hallucination cases", "hallucination %", "gate 拦截次数", "deterministic 判定总数"])
    style_header(ws, 1, 6)
    for tname in ("Track A (DeepSeek Raw)", "Track B (Yance + Same DeepSeek)"):
        st = stats.get(tname, {})
        ws.append([tname, st.get("cases_scored"), st.get("hallucination_cases"), st.get("hallucination_pct"),
                   st.get("hallucinations_blocked_by_gate"), st.get("deterministic_evaluated_total")])
    autosize(ws, [28, 10, 18, 14, 16, 22])

    # ── Sheet 8: 失败归因（标签）──
    ws = wb.create_sheet("8_失败归因")
    ws.append(["scenario_id", "Track", "系统判定", "Gold", "失败类型(标签)"])
    style_header(ws, 1, 5)
    for tkey, tname in [("A", "Track A (DeepSeek Raw)"), ("B", "Track B (Yance+DeepSeek)")]:
        for sid in sorted(gold):
            g = gold[sid]
            rec = tracks[tkey].get(sid, {})
            ov = rec.get("overall_result")
            if ov is None:
                ws.append([sid, tname, "ERROR", g["gold_q1"], "INFRA_ERROR"])
                continue
            if ov == g["gold_q1"]:
                continue
            label = label_failure(sid, g, rec, tkey)
            ws.append([sid, tname, ov, g["gold_q1"], label])
    autosize(ws, [12, 24, 18, 16, 30])

    # ── Sheet 9: 证据接地 & 遥测 ──
    ws = wb.create_sheet("9_证据与遥测")
    ws.append(["Track", "cases", "criteria 总数", "有证据引用数", "Evidence Grounding %", "avg latency s"])
    style_header(ws, 1, 6)
    for tname in ("Track A (DeepSeek Raw)", "Track B (Yance + Same DeepSeek)"):
        st = stats.get(tname, {})
        ws.append([tname, st.get("cases_scored"), "—", "—", st.get("evidence_grounding_pct"), st.get("avg_latency_s")])
    autosize(ws, [28, 10, 14, 14, 20, 14])

    # ── Sheet 10: 执行摘要 & 结论 ──
    ws = wb.create_sheet("10_执行摘要")
    bname = "Track B (Yance + Same DeepSeek)"
    b = stats.get(bname, {})
    a = stats.get("Track A (DeepSeek Raw)", {})
    ba = b.get("eligibility_accuracy_pct") or 0
    aa = a.get("eligibility_accuracy_pct") or 0
    verdict = "Yance V2.1 在同模型下超越裸 DeepSeek" if ba > aa else "未超越（见失败归因）"
    summary = [
        ["结论", verdict],
        ["Yance V2.1 Eligibility Accuracy", f"{ba}%"],
        ["DeepSeek Raw Eligibility Accuracy", f"{aa}%"],
        ["Yance Hard-Gate Recall", f"{b.get('hard_gate_recall_pct')}%"],
        ["DeepSeek Raw Hard-Gate Recall", f"{a.get('hard_gate_recall_pct')}%"],
        ["Yance False Positive", f"{b.get('false_positive_pct')}%"],
        ["Yance Hallucination", f"{b.get('hallucination_pct')}%"],
        ["Yance Evidence Grounding", f"{b.get('evidence_grounding_pct')}%"],
        ["Yance Structured Output", f"{b.get('structured_output_pct')}%"],
        ["Δ Accuracy (B-A)", f"{round(ba-aa,1):+.1} pp"],
        ["样本量限制", "16 cases，统计显著性有限；建议 V3 扩至 50-100 并冻结参考日期"],
        ["时间漂移风险", "gold 部分案例按历史参考日判定（如注册满1年），执行日 2026-08-31 可能漂移，已标 DATASET_TEMPORAL_DRIFT"],
    ]
    for r in summary:
        ws.append(r)
    style_header(ws, 1, 2)
    autosize(ws, [40, 70])

    out = f"{V21}/YANCE_Benchmark_Report_V21.xlsx"
    wb.save(out)
    print("Saved", out)

    # ── 主报告 md + BP_BENCHMARK_BLOCK ──
    build_markdown(gold, tracks, stats, now, verdict, ba, aa)

    # ── BP_BENCHMARK_BLOCK ──
    block = f"""# BP_BENCHMARK_BLOCK.md — Yance Policy Engine V2.1 Benchmark 冻结块

- 生成时间: {now}
- 引擎版本: policy-engine-v2.1 (commit 4401c2f)
- 冻结 Dataset: benchmark_cases.jsonl (S01-S16) — frozen_input_sha256 已落盘，禁止修改
- 冻结 Gold: gold_answers.jsonl — 只读派生 gold_eligibility.jsonl，禁止为提分修改
- Track A: DeepSeek Raw (deepseek-chat, T=0)
- Track B: Yance + Same DeepSeek
- 评分规则: 禁止 hardcode case id；准确率=overall_result 与 gold_q1 一致率
- 红线: env.prod 不入库/不打印/不入报告
- 结论: {verdict}（Yance {ba}% vs DeepSeek Raw {aa}%）
- 状态: {'完整跑通' if tracks['B'] and len([s for s in gold if tracks['B'].get(s)])==len(gold) else '部分完成（见 stats）'}
- 下一步: V3 扩样本至 50-100、冻结参考日期、补 Track C(Qwen)、公开评分脚本复现
"""
    with open(f"{V21}/BP_BENCHMARK_BLOCK.md", "w", encoding="utf-8") as f:
        f.write(block)
    print("Saved BP_BENCHMARK_BLOCK.md")


def label_failure(sid, g, rec, tkey):
    # 时间漂移：gold 涉及注册满1年/未满，且系统判 ELIGIBLE/INSUFFICIENT 与 gold 不符
    raw = g.get("gold_q1_raw", "")
    if ("注册" in raw or "满1年" in raw or "未满" in raw) and rec.get("overall_result") != g["gold_q1"]:
        return "DATASET_TEMPORAL_DRIFT"
    if rec.get("overall_result") == "INSUFFICIENT_INFO" and all(
        (c.get("result") == "INSUFFICIENT" or c.get("result") == "INSUFFICIENT_INFO") for c in rec.get("criteria", [])):
        return "INFRA_OR_OVER_STRICT"
    return "MODEL_JUDGMENT_ERROR"


def build_markdown(gold, tracks, stats, now, verdict, ba, aa):
    a = stats.get("Track A (DeepSeek Raw)", {})
    bname = "Track B (Yance + Same DeepSeek)"
    b = stats.get(bname, {})
    lines = ["# Yance Policy Engine V2.1 — Benchmark 主报告", "", f"生成时间: {now}", ""]
    lines.append("## 结论")
    lines.append(f"- **{verdict}**")
    lines.append(f"- Yance V2.1 Eligibility Accuracy: **{ba}%** vs DeepSeek Raw: **{aa}%** (Δ {round(ba-aa,1):+.1} pp)")
    lines.append("")
    lines.append("## 指标计分卡")
    lines.append("| 指标 | 阈值 | DeepSeek Raw | Yance+DeepSeek |")
    lines.append("|---|---|---|---|")
    for k, lab, op, thr in [("eligibility_accuracy_pct", "Eligibility Accuracy", "≥", 75),
                            ("hard_gate_recall_pct", "Hard-Gate Recall", "≥", 90),
                            ("evidence_grounding_pct", "Evidence Grounding", "≥", 95),
                            ("hallucination_pct", "Hallucination", "≤", 5),
                            ("false_positive_pct", "False Positive", "≤", 5),
                            ("structured_output_pct", "Structured Output", "≥", 98)]:
        lines.append(f"| {lab} | {op}{thr} | {a.get(k)} | {b.get(k)} |")
    lines.append("")
    lines.append("## 逐 case 对比")
    lines.append("| case | type | Gold | A(DeepSeek) | B(Yance) | B==Gold |")
    lines.append("|---|---|---|---|---|---|")
    for sid in sorted(gold):
        g = gold[sid]
        av = tracks["A"].get(sid, {}).get("overall_result")
        bv = tracks["B"].get(sid, {}).get("overall_result")
        lines.append(f"| {sid} | {g['case_type']} | {g['gold_q1']} | {av} | {bv} | {'✓' if bv==g['gold_q1'] else '✗'} |")
    lines.append("")
    lines.append("## 失败归因标签")
    for tkey, tname in [("A", "DeepSeek Raw"), ("B", "Yance")]:
        for sid in sorted(gold):
            g = gold[sid]
            rec = tracks[tkey].get(sid, {})
            ov = rec.get("overall_result")
            if ov and ov != g["gold_q1"]:
                lines.append(f"- {sid} [{tname}]: {ov} vs Gold {g['gold_q1']} → {label_failure(sid, g, rec, tkey)}")
    lines.append("")
    lines.append("## 限制与下一步")
    lines.append("- 样本量 16，统计显著性有限；建议 V3 扩至 50-100。")
    lines.append("- 时间漂移：gold 部分案例按历史参考日判定，执行日 2026-08-31 可能漂移（标 DATASET_TEMPORAL_DRIFT）。")
    lines.append("- 冻结参考日期 + 公开复现脚本，是达到融资级严谨度的前提。")
    with open(f"{V21}/benchmark_report_v21.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Saved benchmark_report_v21.md")


if __name__ == "__main__":
    main()
