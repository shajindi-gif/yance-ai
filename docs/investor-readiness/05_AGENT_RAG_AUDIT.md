# Agent、RAG 与 Evaluation 审计

## 总评

> Orchestrator/Worker 划分、统一 Harness 数据模型、Verified Agent Loop、Hybrid RAG、Structured Policy Layer 与五类 Eval 的实施规格见 `12_AGENT_ARCHITECTURE_RAG_EVAL_SPEC.md`。

仓库已经具备“AI 产品工程意识”：模型 Provider 抽象、pgvector、确定性资格 Gate、Evidence Gate、Golden Cases、benchmark、AgentRun 和 Task 都存在。这比单纯聊天包装更接近 Vertical Agent。

但这些组件尚未组成一个可信系统。当前存在两套含义不同的政策判断：

1. 主报告匹配器：whole-policy embedding + 规则加分，输出 0–100 分和材料关键词；
2. 独立 policy engine：LLM 抽取/判断 + deterministic final gate，输出 ELIGIBLE/NOT_ELIGIBLE/INSUFFICIENT。

主产品主要展示第一套，把“相关性/启发式匹配度”视觉上接近“资格”；第二套 benchmark 未达标，也没有被纳入报告交付和人工复核状态机。这是首要产品与架构风险。

## 当前 Agent 架构

### 模型路由

- Qwen、DeepSeek、OpenAI-compatible、Anthropic 和 mock provider。
- chat completion 直接用 `httpx.AsyncClient(timeout=90)`，没有 retry/backoff、circuit breaker、quota、budget、cache、redaction 或 content policy。
- embedding registry 固定使用 Qwen `text-embedding-v3` 1024 维；配置中的 embedding model/provider 没有真正控制 registry。
- 报告选择 provider，但无 per-tenant allowlist、数据地域策略或模型能力路由。

### 任务

Task worker 用多个 AgentRun 名称描述 pipeline，但 profile_reader 只是加载数据库，report_generator 是 WeasyPrint，policy_match_agent 才调用 embedding。AgentRun 的 token/cost/input/output/evidence 没有完整记录；质量分是硬编码 88。

因此当前更准确的定义是“带步骤日志的异步报告函数”，不是具备工具权限、可恢复计划、审批与评测的 Agent runtime。

## RAG 审计

### 当前实现

- 只在 Policy 整体 `content` 上保存一个 1024 维向量（`models.py:82-111`）。
- company profile 被拼接成一行文本，向量检索全局已发布政策 Top 50（`report/matcher.py:36-63`）。
- 随后基于地区、行业、规模、资质、技术、财务和语义相似度加分。
- `PgVectorStore` 抽象仍按 tenant policy 查询，与主 matcher 的 global policy 语义不同，且未在主要流程使用。

### 缺失的企业级 RAG 能力

| 优先级 | 缺口 | 为什么重要 |
|---|---|---|
| P1 | source/version/document/chunk 模型 | 无法定位原文、处理政策更新或复现历史结论 |
| P1 | 页码/段落/字符 offset 与 citation | 不能向客户证明答案来自哪里 |
| P1 | hybrid retrieval + metadata filter + rerank | whole-document embedding 对长政策和硬门槛不稳定 |
| P1 | tenant ACL 与 global/private visibility | 当前 global/tenant 查询互相冲突 |
| P1 | ingestion pipeline | 上传资料不能进入画像或检索 |
| P1 | retrieval evaluation | 没有 recall@k、MRR、citation precision、answer faithfulness |
| P1 | policy validity/version | 没有失效、替代、附件、通知、来源健康状态 |
| P2 | query rewriting/multi-hop | 企业事实、政策条件和材料证据需要多集合检索 |

## 匹配算法风险

- 政策要求高企，而公司没有高企时仍加 5 分；规模、技术和财务也有默认分。最终“匹配度”可能较高，但不代表资格。
- 地区判断代码把 `company.city` 与 `policy.district` 比较，缺少 company district 字段。
- `company_age_years` 被读取但未使用。
- 每次匹配都 insert 新 Opportunity，没有 `(company, policy, profile_version, policy_version, engine_version)` 唯一约束或 upsert。
- evidence 仅包含分数组成和通用材料清单，不包含政策原文片段或企业材料引用。
- PDF 资格矩阵每行都写“待系统判断”（`report/pdf.py:176-197`），说明报告并未真正完成资格判断。

建议立即把输出命名拆开：`relevance_score`、`eligibility_decision`、`evidence_coverage`、`confidence`，禁止用一个百分比分数承载四种含义。

## Policy Engine 安全问题

### P0：硬门槛被错误软化

`_SOFT_PAT` 把“未发生安全事故、环境违法、社会信用”等条件识别为 advisory，并且 `_is_blocking` 先判断 soft pattern，再判断“须/必须/不得”等强制词（`deterministic.py:414-433`）。因此这些政策硬门槛 FAIL 可被排除在 final gate 之外，最终输出 ELIGIBLE。

修复不能只改一个正则。应建立：

- 明确的 hard-gate taxonomy 和政策 DSL；
- 否定、时间窗、主体、金额、比例和组合条件解析；
- 未识别条件默认 blocking/INSUFFICIENT；
- 安全、信用、合规、地域、资质、截止日的专门回归集；
- 高风险结论人工批准。

### P0/P1：Evidence Gate 可被子串绕过

unsupported 判断包含 `n.rstrip('%％') not in full_norm`（`evaluator.py:224-235`）。政策原文有 `140%` 时，伪造的 `40%` 会因裸字符串 `40` 出现在 `140` 中而被接受。金额、人数等也可能出现相同边界问题。

应解析为带单位和上下文的 typed quantity，并要求 exact token span，不做裸 substring 检查。

### Prompt injection 和数据治理

- 政策正文与用户查询直接拼入 prompt，没有把不可信文档和系统指令隔离。
- 无 prompt injection 检测、tool allowlist、output schema firewall、PII/商业秘密脱敏。
- 无模型供应商数据处理 policy enforcement；页面却承诺 zero retention。
- 原始 provider response 可能包含敏感数据，存储、保留和访问策略未定义。

## Evaluation 审计

### 仓库内 eval

`yance-ai/evals/run_evals.py` 只验证 JSONL 是否包含 `id/input/expected/tags/eligible`，不会调用任何模型或引擎，也不比较预测。CI 即使有效，这一步也不能阻止质量回归。

### V2.2 benchmark

提交的主报告显示：

- Eligibility Accuracy 43.8%，阈值 75%；
- Hard-Gate Recall 71.4%，阈值 90%；
- False Positive 28.6%，阈值 ≤5%；
- 样本量仅 16；报告自己承认未超越裸 DeepSeek。

这组数据应被视为正面的工程透明度，但结论非常明确：不能生产自动判定。benchmark 脚本还包含本机绝对路径依赖，错误/缺失样本在部分脚本中可能不进入分母；需要完全可复现化。

## 建议 Evaluation 体系

### 数据集分层

1. Parser unit cases：数字、单位、否定、时间、主体、组合条件；
2. Retrieval set：query → expected source/chunks；
3. Eligibility set：按政策类型、地区、企业阶段、边界/对抗样本分桶；
4. Draft quality set：事实一致性、字段完整性、引用、模板要求；
5. Workflow set：失败重试、人工拒绝、政策版本变化、资料冲突；
6. Security set：prompt injection、数据外泄、跨租户 retrieval、恶意文档。

### 指标与发布 Gate

| 指标 | 建议 Gate |
|---|---:|
| Hard-gate recall | ≥95% |
| 严重假阳性 | ≤2% |
| Overall accuracy | ≥85%，并按政策类型报告 |
| Retrieval recall@10 | ≥95% |
| Citation precision | ≥98% |
| 无证据关键断言率 | ≤1% |
| Structured output valid | ≥99.5% |
| Task success/recovery | ≥99% / 100% recoverable |
| 人工重大改写率 | 作为产品学习指标持续下降，不得隐藏 |

阈值需用不少于 100–300 条、双人标注且有 adjudication 的冻结集验证；线上 shadow/canary 不能复用训练 prompt 调试集。

## 目标 Agent 架构

```text
Task Command
  → workflow snapshot (tenant/profile/policy/template/version)
  → planner with allowed step graph
  → deterministic retrieval and hard-gate tools
  → LLM synthesis only where needed
  → evidence validator + policy validator + security validator
  → human approval checkpoint
  → immutable deliverable + audit trail
```

每一步记录：input/output hash、source IDs、model/provider/version、prompt version、latency、tokens、estimated cost、retries、validator results、actor 和 timestamps。敏感正文不应默认进入日志。

## 修复优先级

### P0

- 修复 blocking taxonomy 和 Evidence Gate；冻结自动 ELIGIBLE，默认人审。
- 明确“匹配”与“资格”两个对象和 UI 术语。

### P1

- 建 source/version/chunk/citation/decision snapshot 模型和 ingestion pipeline。
- 持久 workflow、Model Gateway、预算/重试/脱敏/trace。
- 将 eval 变成真实执行 Gate，并扩充分桶数据集。

### P2

- hybrid retrieval、reranker、政策变更增量重评、draft template/eval、tenant knowledge overlay。

### P3

- 多 Agent 扩展、自动模型选择和跨 vertical 复用；只有在单一 Golden Journey 指标稳定后推进。

## Phase 5 remediation status — 2026-09-04

Implemented and verified:

- policy source versions, exact-span chunks, checksums, metadata, and opportunity-level source pinning;
- tenant-aware lexical/vector reciprocal-rank fusion with a clearly identified legacy fallback;
- typed eligibility rules and a deterministic four-state engine;
- exact citation persistence and a verifier gate inside the durable Agent Harness;
- criterion/evidence/material/benefit APIs and an inspectable opportunity UI;
- additive migration, PostgreSQL tests, OpenAPI refresh, production frontend build, and browser checks.

Still open by design:

- document-format ingestion and company-document RAG;
- learned reranking and automated policy-change re-evaluation;
- reviewed human approval state for final `ELIGIBLE`;
- real benchmark execution and Admin Eval reporting.

The original benchmark warning remains active. This remediation improves provenance and fail-closed behavior; it does not establish production accuracy by itself.
