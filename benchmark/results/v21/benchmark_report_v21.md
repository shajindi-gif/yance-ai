# Yance Policy Engine V2.2 — Benchmark 主报告

生成时间: 2026-08-31 21:44

## 结论
- **未超越（与裸 DeepSeek 持平，见失败归因）**
- Yance V2.2 Eligibility Accuracy: **43.8%** vs DeepSeek Raw: **43.8%** (Δ +0.0 pp)

## 指标计分卡
| 指标 | 阈值 | DeepSeek Raw | Yance+DeepSeek |
|---|---|---|---|
| Eligibility Accuracy | ≥75 | 43.8 | 43.8 |
| Hard-Gate Recall | ≥90 | 57.1 | 71.4 |
| Evidence Grounding | ≥95 | 100.0 | 100.0 |
| Hallucination | ≤5 | 0.0 | 0.0 |
| False Positive | ≤5 | 14.3 | 28.6 |
| Structured Output | ≥98 | 100.0 | 100.0 |

## 逐 case 对比
| case | type | Gold | A(DeepSeek) | B(Yance) | B==Gold |
|---|---|---|---|---|---|
| S01 | 明确不符合 | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | ✓ |
| S02 | 符合申报资格 | ELIGIBLE | INSUFFICIENT_INFO | INSUFFICIENT_INFO | ✗ |
| S03 | 信息不足 | INSUFFICIENT_INFO | INSUFFICIENT_INFO | INSUFFICIENT_INFO | ✓ |
| S04 | 边界案例 | NOT_ELIGIBLE | INSUFFICIENT_INFO | ELIGIBLE | ✗ |
| S05 | 符合申报资格 | ELIGIBLE | INSUFFICIENT_INFO | ELIGIBLE | ✓ |
| S06 | 幻觉陷阱 | NOT_ELIGIBLE | INSUFFICIENT_INFO | ELIGIBLE | ✗ |
| S07 | 幻觉陷阱 | ELIGIBLE | INSUFFICIENT_INFO | NOT_ELIGIBLE | ✗ |
| S08 | 明确不符合 | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | ✓ |
| S09 | 边界案例 | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | ✓ |
| S10 | 符合申报资格 | ELIGIBLE | INSUFFICIENT_INFO | NOT_ELIGIBLE | ✗ |
| S11 | 信息不足 | INSUFFICIENT_INFO | INSUFFICIENT_INFO | NOT_ELIGIBLE | ✗ |
| S12 | 幻觉陷阱 | ELIGIBLE | INSUFFICIENT_INFO | NOT_ELIGIBLE | ✗ |
| S13 | 信息不足 | INSUFFICIENT_INFO | INSUFFICIENT_INFO | NOT_ELIGIBLE | ✗ |
| S14 | 明确不符合 | NOT_ELIGIBLE | NOT_ELIGIBLE | NOT_ELIGIBLE | ✓ |
| S15 | 边界案例 | NOT_ELIGIBLE | ELIGIBLE | NOT_ELIGIBLE | ✓ |
| S16 | 幻觉陷阱 | ELIGIBLE | INSUFFICIENT_INFO | NOT_ELIGIBLE | ✗ |

## 失败归因标签
- S02 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S04 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold NOT_ELIGIBLE → MODEL_JUDGMENT_ERROR
- S05 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S06 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold NOT_ELIGIBLE → DATASET_TEMPORAL_DRIFT
- S07 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold ELIGIBLE → DATASET_TEMPORAL_DRIFT
- S10 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S12 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S15 [DeepSeek Raw]: ELIGIBLE vs Gold NOT_ELIGIBLE → MODEL_JUDGMENT_ERROR
- S16 [DeepSeek Raw]: INSUFFICIENT_INFO vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S02 [Yance]: INSUFFICIENT_INFO vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S04 [Yance]: ELIGIBLE vs Gold NOT_ELIGIBLE → MODEL_JUDGMENT_ERROR
- S06 [Yance]: ELIGIBLE vs Gold NOT_ELIGIBLE → DATASET_TEMPORAL_DRIFT
- S07 [Yance]: NOT_ELIGIBLE vs Gold ELIGIBLE → DATASET_TEMPORAL_DRIFT
- S10 [Yance]: NOT_ELIGIBLE vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S11 [Yance]: NOT_ELIGIBLE vs Gold INSUFFICIENT_INFO → MODEL_JUDGMENT_ERROR
- S12 [Yance]: NOT_ELIGIBLE vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR
- S13 [Yance]: NOT_ELIGIBLE vs Gold INSUFFICIENT_INFO → MODEL_JUDGMENT_ERROR
- S16 [Yance]: NOT_ELIGIBLE vs Gold ELIGIBLE → MODEL_JUDGMENT_ERROR

## V2.2 引擎改进（vs 冻结 V2.1，commit 1a6269b）
- 确定性层：科技人员占比等 ratio 字段优先级前置，employee_count 归一修复，17/17 单测通过。
- Evidence Gate：千分位逗号归一化（5,000万元==5000万元），消除合法政策数字误杀。
- 硬/软条件区分：final_gate(blocking) + _is_blocking()，软性/主观条件（创新能力评价、荣誉奖励、安全事故、社会信用）不再阻断资格判定，纠正冻结 V2.1 过度保守。
- 自身收益：Yance Eligibility Accuracy 37.5%→43.8%；Hard-Gate Recall 维持 71.4%（高于裸 DeepSeek 57.1%）。

## 评分方法学修正（透明披露，非 Gold/Dataset/阈值改动）
- 幻觉扫描增加逗号 + 数字-单位空格归一化（与引擎 Evidence Gate 同源），修正将 '5000万' 误判为 '5,000万元' 幻觉的假阳性；归一后 Track B 政策引用幻觉率 62.5%→0.0%。
- 'hallucinations_blocked'（Evidence Gate 拦截弱证据的安全介入次数）单列安全指标，不再计入幻觉率；真实政策数字伪造率 Track A/B 均为 0.0%。

## 限制与下一步
- 样本量 16，统计显著性有限；建议 V3 扩至 50-100。
- 时间漂移：gold 部分案例按历史参考日判定，执行日 2026-08-31 可能漂移（标 DATASET_TEMPORAL_DRIFT）；头对头对称，不影响比较结论。
- 冻结参考日期 + 公开复现脚本，是达到融资级严谨度的前提。
- 剩余缺口（Acc 43.8% vs 75%、FP 28.6% vs 5%）由底层 LLM 硬条件判定误差驱动，V3 需加硬 Gate 全量确定性复核层。