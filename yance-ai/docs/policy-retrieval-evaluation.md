# 政策检索与对照评测

代码：`app/services/park_policy/retrieval.py`、`app/services/park_policy/evaluation.py`
评测集：`config/eval/park_policy_eval_v1.yaml`（版本 `2026-11-06.1`，digest `2191663da79c70c0`）
实测报告：`docs/evidence/eval-report-2026-11-06.json`
复现：`python scripts/park_policy/cli.py eval run --out docs/evidence/eval-report-<date>.json`

---

## 1. 结论先行

| 结论 | 状态 |
| --- | --- |
| 工程类测试（权限、状态、规则、故障） | **已实测，可引用下方数字** |
| 真实政策检索与引用测试 | **阻塞**：本地无入库政策，无 DB |
| 企业资格业务评测 | **阻塞**：无授权脱敏企业样本 |
| "比通用大模型更精确" | **未证明**，A/B 两臂均因缺供应商配置未运行 |
| 业务准确率 | **不成立**，不得对外声明任何准确率数字 |

工程类通过率 **不得** 用于证明业务准确率。这是本文件最重要的约束。

---

## 2. 三个对照臂

| 臂 | 定义 | 本地状态 |
| --- | --- | --- |
| A `A_general_model` | 选定通用模型，用其常规信息能力作答 | **blocked**：无供应商配置与预算 |
| B `B_same_model_with_corpus` | 同一模型 + 相同政策语料，不用衍策规则与工作流 | **blocked**：同上 |
| C `C_yance_evidence` | 完整检索 + 证据 + 规则流程 | **可运行**（确定性规则核心） |

**禁止事项**：不得用更弱基线冒充 A/B；不得把离线能力伪装成联网；不得为了让 C 好看而故意削弱基线。`evaluation.py` 中 A/B 为 `runnable=False` 且 `result=None`，测试 `test_model_arms_are_blocked_not_simulated` 强制此约束。

### 为什么 C 现在只有确定性核心

模型辅助抽取阶段需要供应商配置与每日预算，本轮未获批。因此 C 运行的是 `conditions.py` / `evidence.py` / `geography.py` 的确定性规则，**不是 LLM 表现**。报告中 `arm_description.model = "deterministic_rule_core"` 明确标注。

---

## 3. 已实测结果（2026-11-06）

评测集 24 题：engineering 21、retrieval 2（blocked）、eligibility 1（blocked）。

### 3.1 C 臂（确定性规则核心）

| 指标 | 值 |
| --- | --- |
| 评分题数 | 21 |
| behavior_match_rate | **1.0** |
| severe_error_count | **0** |
| invented_support_count | **0** |
| prohibited_violations | **0** |
| 未评分（缺材料） | 3 |

### 3.2 过度声明基线（naive keyword arm）

设此臂的唯一目的：证明评测能抓出"看起来会答、实际无据"的行为。

| 指标 | 值 |
| --- | --- |
| behavior_match_rate | 0.4286 |
| severe_error_rate | **0.5714** |
| invented_support_count | **21 / 21**（每题都无据作答） |

对比说明：C 的 1.0 只证明**规则实现与测试集一致**，不证明业务准确。naive 臂的 21 次无据声明说明：如果不做证据约束，行为正确率看着过半，实际每次都编造。

### 3.3 分类表现（C 臂）

| 类别 | 题数 | behavior_match |
| --- | --- | --- |
| geography | 3 | 1.0 |
| dates | 4 | 1.0 |
| amounts | 3 | 1.0 |
| eligibility | 4 | 1.0 |
| security | 4 | 1.0 |
| versioning | 3 | 1.0 |

---

## 4. 题目覆盖（应测清单）

| 应测项 | 题号 | 是否覆盖 |
| --- | --- | --- |
| 地区/园区归属错误 | ENG-GEO-001/002/003 | 是 |
| 政策已过期与申报已截止 | ENG-DATE-001 | 是 |
| 新旧批次冲突 | ENG-DATE-003 | 是 |
| 金额上限、比例、单位、统计期间 | ENG-AMT-001/002/003 | 是 |
| 附件隐藏条件 | — | **未覆盖**（无真实附件） |
| 企业证据缺失/矛盾 | ENG-ELI-001/002 | 是 |
| 同名政策与来源更新 | ENG-VER-001/002/003 | 是 |
| 不得重复享受 | ENG-ELI-004 | 是 |
| 提示注入与跨租户检索 | ENG-SEC-001~004 | 是 |
| 真实政策 Recall@K | RET-001/002 | **blocked** |
| 企业资格端到端 | ELI-BIZ-001 | **blocked** |

---

## 5. 报告指标口径

必须分别报告，禁止合成总分（`headline_score` 恒为 `null`）：

| 指标 | 本地可得 | 说明 |
| --- | --- | --- |
| 来源覆盖 | 是 | 见 `park-source-coverage.md` |
| 更新延迟 | 否 | 无生产运行 |
| 解析质量 | 否 | 无入库解析 |
| Recall@K | 否 | 无真实语料 |
| 引用支持率 | 否 | 同上 |
| 错误判为符合 | 部分 | 工程题中 `not_satisfied`/`needs_review` 收敛正确 |
| 错误排除机会 | 否 | 需真实样本 |
| 证据不足识别 | 是 | ENG-ELI-001 |
| 合理拒答 | 是 | RET/ELI 臂定为 `insufficient_evidence` |
| 任务完成率 | 否 | 无端到端 |
| 延迟与单次成本 | 否 | 无模型调用 |

---

## 6. 数据集隔离

评测集声明 `splits.dev` / `splits.test` 及各自 `policy_families`。`validate_eval_set` 强制：同一政策家族不得跨 split 出现，否则报"评测泄漏"并拒绝运行（`test_validation_catches_family_leak` 验证）。

当前评测集使用 `demo_family_a/b/c` 占位家族，接入真实政策时必须替换为真实家族 ID 并重新核对隔离。

---

## 7. 建立基线后的下一步（需授权）

1. 接入真实政策语料（依赖 DB 与采集落地）
2. 启用 A/B 臂：需要模型版本、每日预算上限、联网方式、测试设置记录
3. 用授权脱敏企业样本做资格评测，标注依据与复核身份；客户确认标签标为**客户自评**，不冒充独立专家真值
4. 先出基线，再提发布阈值与理由

在完成 1–4 之前，对外表述只能是："已建立可复现的评测框架，工程类测试通过，业务准确率尚未验证。"
