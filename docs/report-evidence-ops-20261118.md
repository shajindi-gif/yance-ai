# 证据不足可运营化 · 2026-11-18

结论：当前瓶颈几乎全是 **A 类（缺结构化资格规则）**，不是画像缺字段，也不是引用核验失败。

## 全局覆盖（生产只读）

| 指标 | 值 |
| --- | --- |
| published policies | 1401 |
| published versions | 1744 |
| eligibility_rules 总计 | 1（冒烟注入） |
| active rules | 1 |
| 带 active 规则的 policy_version | 1 |

## 冒烟扫描 50 条机会分类

| 类 | 含义 | 数量 |
| --- | --- | --- |
| A | 缺已审核结构化规则 / 缺硬门槛 | 49 |
| B | 有规则但 source_quote 无法逐字核验 | 0 |
| C | 企业画像缺 fact_key | 0 |
| other | 正例（冒烟合成政策） | 1 |

样本缺口文案共性：`政策尚无已审核的结构化资格规则`，常叠加生效日/截止日/地域未核实。

## 可执行清单（不混提脏采集）

### A · 补结构化规则（最高优先）
1. 从已发布、有原文版本的政策中，按客户高频行业/地域挑 Top N（建议先上海 + 人工智能/专精特新）。
2. 每条政策至少 1 条 `is_hard_gate=true` 的 `EligibilityRule`，`source_quote` 必须能在 `PolicyVersion.content` + `PolicyChunk` 逐字命中。
3. 入库前用现有 exact-span 校验；失败进 B，不得标 active。
4. 目标：使客户扫描里「带 verified 引用的正例/可操作 NEED_MORE」占比上升，而不是降低 NEED_MORE 总数靠编造。

### B · 修复不可核验 quote
1. 规则创建/导入流水线强制 `exact_quote_span(version.content, source_quote)`。
2. quote 漂移：回写原文片段或停用规则，禁止「差不多」匹配。

### C · 画像 fact_key
1. 本轮冒烟未触发 C；规则上线后按 `企业画像缺少：*` 聚合补表单提示与必填引导。
2. MISSING 时仍保留已核验规则原文引用（已上线），避免空简报。

### 明确不做
- 不靠开放 Ask / LLM 写资格结论
- 不提交本机 collector 脏改动作「增产」
- 不把无规则政策标成 ELIGIBLE

## 证据

服务器 `/tmp/evidence_ops_out.json`；脚本 `/opt/yance/releases/report-20261118-01/evidence_ops.py`。
