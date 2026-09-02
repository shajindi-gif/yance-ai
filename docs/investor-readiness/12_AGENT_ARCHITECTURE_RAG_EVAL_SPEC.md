# Agent Architecture、Harness、RAG、Policy Layer 与 Eval 规格

审计日期：2026-09-02

适用范围：Sections 5–10 目标架构

依赖：`05_AGENT_RAG_AUDIT.md`、`11_AGENT_WORKFLOW_AUDIT.md`

## 结论

当前系统还不是统一 Agent Runtime：

- `LLMRouter` 只负责按字符串选择模型供应商；
- `AgentRun` 只有 agent/provider/model/status/token/latency/error/metadata 等摘要字段，并且允许客户端直接创建和结束；
- Task 后台函数手工创建 `profile_reader`、`policy_match_agent`、`report_generator` 三条记录，但没有 Plan、AgentStep、ToolCall、Verification、Retry 或不可变轨迹；
- 关键报告路径仍是“拼 Prompt → 调 LLM → 返回文本”；
- RAG 只在整篇 Policy 上保存单一 embedding，无 Chunk、BM25、Rerank、Context Builder 和 Citation；
- `PolicyRule.rule_json` 是自由 JSON，不构成可执行、版本化的政策结构层；
- `yance-ai/evals/run_evals.py` 只校验测试文件字段，不执行系统、不产生 model answer 或 score；
- benchmark 有真实输出，但只有 16 例、脚本依赖本机绝对路径，且没有统一 EvalRun 数据模型或 Admin Dashboard。

目标应是一个 **结构化、可恢复、可验证、可审计的 Agent Harness**。LLM 只能参与受限步骤，不能代替 workflow、policy rule engine、evidence validator 或最终状态机。

## 非协商原则

1. Agent 输入和输出必须通过 Pydantic/JSON Schema 校验；自由文本只能作为某个结构化字段中的 draft/summary。
2. Orchestrator 不直接拥有无限工具；每个 Worker 使用最小权限 allowlist。
3. 所有关键结果先进入 `review` 或验证 Gate，Verifier 失败不能 `completed`。
4. Retrieval 和生成必须固定 tenant/workspace、source version 和 evidence IDs。
5. Retry 是显式对象，不允许在 SDK 内静默无限重试。
6. AgentRun/Step/ToolCall/Evidence/Artifact/Evaluation/Error/Retry 形成不可变或追加式轨迹。
7. 运行指标来自真实执行；没有运行就显示 `No evaluation data yet.`，禁止 seed 假指标。
8. Policy eligibility 以结构化规则和确定性聚合为主，LLM 只做提取建议、语义判断和解释。

## 目标运行架构

```text
User/API/Scheduler
       │
       ▼
Workflow Command ── idempotency key / tenant / workspace / actor
       │
       ▼
Orchestrator Agent
  Plan → Route → Execute → Verify → Retry/Review → Finish
       │
       ├─ CompanyProfileAgent
       ├─ DocumentAnalysisAgent
       ├─ PolicySearchAgent
       ├─ EligibilityAgent
       ├─ EvidenceAgent
       ├─ ApplicationAgent
       ├─ ReportAgent
       └─ QAAgent / deterministic verifiers
       │
       ▼
Agent Harness
  Run / Step / ToolCall / Evidence / Artifact / Evaluation / Error / Retry
       │
       ├─ Durable queue + lease + outbox
       ├─ Tool registry + policy engine
       ├─ Retrieval service + citation builder
       ├─ Model gateway + budgets
       └─ Trace/metrics/audit/admin
```

## Agent Catalog

| Agent | 结构化输入 | 结构化输出 | 允许工具 | 强制 Verifier |
|---|---|---|---|---|
| OrchestratorAgent | WorkflowRequest、当前 snapshot、policy | ExecutionPlan / FinalRunResult | 只可 route/inspect/cancel；不能直接查询任意数据 | Plan schema、dependency graph、finish gate |
| CompanyProfileAgent | DocumentSpan IDs、已有 ProfileVersion、ExtractionSchema | ProposedCompanyFacts、conflicts、coverage | document reader、fact extractor、profile repository | fact provenance、type/unit、conflict validator |
| DocumentAnalysisAgent | DocumentVersion、requested operations | ParseResult、SummaryResult、ExtractedFields | sandbox parser/OCR、document store | malware/parse status、span coverage、schema validator |
| PolicySearchAgent | SearchIntent、CompanyProfileVersion、filters | RankedOpportunityCandidates、RetrievalTrace | hybrid retrieval、metadata filter、reranker | ACL、source validity、citation coverage |
| EligibilityAgent | ProfileVersion、ProgramVersion、EligibilityRuleVersion | CriterionResults、proposed overall state | rule evaluator、fact lookup、limited semantic judge | deterministic final gate、hard-rule coverage |
| EvidenceAgent | CriterionResults、retrieval snapshot | EvidenceBundle、unsupported claims | source span resolver、citation validator | exact span、source/version/tenant validation |
| ApplicationAgent | Approved facts、requirements、template version | DraftApplication、RequiredMaterials、Tasks | template engine、approved fact reader | field completeness、citation、unsupported claim scan |
| ReportAgent | Approved assessment/artifacts、report schema | ReportArtifact manifest | renderer/exporter only | template schema、format validation、safe rendering |
| QAAgent | Candidate output、expected schema、risk tier | VerificationResult、EvaluationScores | deterministic validators、optional judge model | QA 本身不得自我豁免；高风险需 human review |

Worker 不能接收未限定的自然语言“帮我处理一下”。每个调用必须包含 `operation`、typed input references、expected output schema、risk tier、deadline 和 budget。

## 结构化 Contract

### 基础请求

```python
class WorkflowRequest(BaseModel):
    workflow_id: UUID
    workflow_version: str
    tenant_id: UUID
    workspace_id: UUID
    user_id: UUID | None
    operation: WorkflowOperation
    input_refs: list[ResourceRef]
    parameters: dict[str, JsonValue]
    expected_output_schema: str
    risk_tier: Literal["low", "medium", "high", "critical"]
    idempotency_key: str
```

### Plan

```python
class PlanStep(BaseModel):
    step_key: str
    agent_id: AgentId
    operation: str
    input_refs: list[ResourceRef]
    depends_on: list[str]
    allowed_tools: list[str]
    verifier_ids: list[str]
    max_attempts: int = Field(ge=1, le=5)
    timeout_seconds: int = Field(ge=1, le=1800)

class ExecutionPlan(BaseModel):
    objective: str
    steps: list[PlanStep]
    finish_conditions: list[FinishCondition]
    requires_human_review: bool
```

### Worker 输出

```python
class AgentResult(BaseModel):
    status: Literal["succeeded", "needs_input", "rejected"]
    output_schema: str
    output: dict[str, JsonValue]
    evidence_ids: list[UUID]
    artifact_ids: list[UUID]
    warnings: list[StructuredWarning]
    confidence: float = Field(ge=0, le=1)
```

### Verification

```python
class VerificationResult(BaseModel):
    passed: bool
    verifier_id: str
    verifier_version: str
    checks: list[VerificationCheck]
    evidence_ids: list[UUID]
    failure_codes: list[str]
    recommended_action: Literal["finish", "retry", "human_review", "fail"]
```

Schema 名称必须映射到版本化 JSON Schema registry；运行时保存 schema name/version 和 input/output hash。Pydantic validation 失败作为结构化 AgentError，不把不合法输出保存为成功结果。

## Orchestrator Agent

### 职责

- `plan`：从已注册 workflow definition 选择有向无环步骤，不自由发明工具；
- `route`：按 operation/risk/data policy 选择 Worker、model 和 verifier；
- `execute`：把 Step 投递到 durable queue，维护依赖和 lease；
- `verify`：聚合每步 VerificationResult；
- `retry`：只依据 ErrorPolicy 创建 RetryAttempt；
- `finish`：检查 artifact/evidence/review/quality Gate 后关闭 Run。

### 禁止事项

- 不直接拼一个包含所有资料的 mega prompt；
- 不修改 Worker 输出绕过 schema；
- 不在 verifier 失败时自行宣称 completed；
- 不使用未注册 tool/model/prompt；
- 不跨 tenant/workspace 解析 ResourceRef；
- 不把 reasoning chain-of-thought 作为产品日志；只保存简洁结构化 decision summary。

## Agent Harness 数据模型

### AgentRun

统一一次 workflow 执行，替代当前可由客户端伪造的摘要记录。

| 字段 | 要求 |
|---|---|
| id/run_id | UUID，外部展示 run_id |
| tenant_id/workspace_id/user_id | 强制 scope；scheduler/system actor 可无 user |
| agent_id | 当前 owner/orchestrator ID |
| workflow_id/workflow_version | 指向不可变 definition |
| prompt_version | Orchestrator prompt/plan policy 版本；无 LLM 时明确 `none` |
| provider/model/model_version | 实际模型；不使用模型时为 null |
| input_json/output_json | schema-validated；敏感 payload 可只存受限 blob reference + hash |
| input_schema/output_schema | name + version |
| input_tokens/output_tokens | 实际供应商 usage；不可用为 null，不填 0 |
| cost_amount/cost_currency | 由 price catalog 计算，未知为 null |
| latency_ms | run wall time；另存 queue/step/model latency |
| status | 统一状态枚举 |
| tool_call_count/evidence_count/error_count/retry_count | 可校验汇总 |
| started_at/finished_at/created_at/updated_at | UTC |
| trace_id/idempotency_key | 全链路关联与唯一约束 |
| cancellation_reason/failure_code | 结构化终态原因 |

### AgentStep

| 字段 | 要求 |
|---|---|
| run_id / step_key / sequence | 同一 run 唯一 step_key |
| parent_step_id | 支持受控子步骤，不支持无界递归 |
| agent_id / operation | 实际 Worker 和动作 |
| input/output refs + schema/hash | 不复制超大敏感正文 |
| status / attempt_count | 使用同一状态机的 step 子集 |
| queue_ms / latency_ms | 分离排队和执行 |
| verifier_status | pending/passed/failed/review |
| started/finished/lease_expires | 支持恢复 |

### ToolCall

保存 step、tool name/version、structured arguments、argument hash、result reference/hash、status、latency、error、idempotency key、evidence IDs。Tool Call 必须由 registry 校验 allowlist 和 input/output schema。

### Evidence

通用 Evidence 与 Policy Evidence 使用同一基类：tenant/workspace、source type、source/document/version/span、quote、metadata、content hash、confidence、created_by_run/step、verified_at/verifier。Evidence 只引用不可变 source version。

### Artifact

保存 artifact type、MIME、format、schema/template version、storage key、content hash、source snapshot、version、supersedes、review status、created_by_run/step。Deliverable 应成为已批准 Artifact 的业务视图，而不是另存一套不可追踪内容。

### Evaluation

既可以关联生产 AgentRun/Step，也可以属于离线 EvalRun。字段包括 evaluator type/version、dimension scores、pass/fail、evidence、error types、judge model（如有）、human reviewer 和时间。

### AgentError

字段包括 code、category、severity、retryable、sanitized_message、provider status、step/tool reference、fingerprint、occurred_at。原始含敏感数据的错误只进入受限存储，不默认展示。

### RetryAttempt

保存 run/step、attempt number、reason error ID、policy version、backoff、scheduled/started/finished、outcome。`unique(step_id, attempt_number)`，最大次数由 plan 和 error policy 双重限制。

### 关系

```text
AgentRun
  ├─ AgentStep
  │    ├─ ToolCall
  │    ├─ Evidence
  │    ├─ Artifact
  │    ├─ Evaluation
  │    ├─ AgentError
  │    └─ RetryAttempt
  ├─ HumanReview
  └─ ActivityEvent
```

## Harness 状态机

唯一 Run 状态：

```text
queued → planning → running → waiting → running
                          └→ review → running/completed/failed
running/waiting/review → cancelled
planning/running/waiting/review → failed
running/review → completed
```

### 状态约束

- `queued`：已持久化且 outbox/queue 接受；
- `planning`：只允许生成/验证 plan；
- `running`：至少一个可执行 step 有 lease；
- `waiting`：等待外部资源、依赖或 backoff，必须有 wait reason/wake time；
- `review`：等待 human approval，不能自动超时为 completed；
- `completed`：所有 required steps + verifier + required review 通过；
- `failed`：不可重试错误或重试耗尽；
- `cancelled`：显式 actor/reason，worker 必须停止副作用。

非法状态转换由 domain service 和 DB check/transition log 双层阻止。Run status 不能由普通客户端直接 PATCH。

## Agent Loop

```text
Plan
  → Retrieve
  → Reason
  → Act
  → Verify
       ├─ pass → Finish / next step
       ├─ fixable → Retry
       ├─ uncertain/high risk → Human Review
       └─ terminal → Fail
```

### Plan

从 versioned WorkflowDefinition 生成 ExecutionPlan；验证无循环、工具权限、资源 scope、预算、超时和 finish condition。

### Retrieve

通过 RetrievalRequest 调用检索服务，返回 RetrievalSnapshot。Snapshot 保存 query、filters、index versions、candidate scores、rerank scores 和 selected chunk IDs。

### Reason

LLM 仅使用 Context Builder 输出的受限上下文，返回结构化 proposed decision/draft。Reason 不直接产生数据库副作用。

### Act

Tool Registry 执行允许的副作用。每个 ToolCall 有 idempotency key；外部调用先持久化 intent/outbox。

### Verify

按任务风险组合 verifier：schema、citation、rule coverage、unsupported claim、artifact format、安全和 human review。关键任务至少一个非生成模型的确定性 verifier。

### Retry

仅对 transient/provider/schema-repair 等允许类别重试；每次 retry 使用明确 correction input。相同 prompt 的无脑重试不允许。达到上限后进入 review/failed。

### Finish

输出 FinalRunResult，锁定 source snapshot、artifacts、evaluations 和成本。完成后不原地修改；修订创建新 run/version。

## 关键链路：Eligibility

```text
PolicySearchAgent
  → RetrievalSnapshot + ProgramVersion
EligibilityAgent
  → CriterionResults（规则优先）
EvidenceAgent
  → 每条结论的 policy/company evidence
QAAgent / Verifiers
  → hard-rule coverage
  → citation exactness
  → policy validity
  → unsupported claim
Deterministic Final Gate
  → four-state proposed result
Human Review（高风险/ELIGIBLE）
  → final result
```

任何一层缺失或失败，不能从自然语言 summary 推导最终状态。

## Tool Registry 与权限

每个 tool 注册：name/version、input/output schema、read/write、allowed agents、risk tier、timeout、idempotency、tenant scope、network/filesystem policy 和 audit policy。

示例：

- `document.read_spans`：只读指定 DocumentVersion spans；
- `retrieval.search_programs`：强制 workspace/global visibility filters；
- `policy.evaluate_rule`：确定性 typed rule；
- `artifact.render_docx`：只读取 approved facts/template；
- `application.create_task`：写操作，需要 idempotency/outbox；
- `notification.send`：最终外部副作用，需要明确 recipient 和 approval policy。

## Admin Agent Run Trace

后台必须能打开一次 Run 并展示真实轨迹：

1. Run identity：tenant/workspace/user/workflow/version/status；
2. 时间线：queue、plan、step、tool、verify、retry、review、finish；
3. 每步结构化输入/输出 schema 和 hash；敏感值按权限遮蔽；
4. Tool Call 参数、结果、latency 和错误；
5. Evidence 和 Citation 可打开到原文；
6. Artifact 版本和 review；
7. Evaluations、failure codes 和 verifier versions；
8. tokens、cost、model latency、queue latency；
9. retry/cancel actor 和原因；
10. trace/request IDs。

平台管理员可跨租户查看必须使用独立 platform role、reason 和 audit；租户管理员只能查看本组织运行。

## RAG 当前状态

| 能力 | 当前实现 | 结论 |
|---|---|---|
| Parse/Clean | 无 policy ingestion pipeline | 缺失 |
| Metadata | Policy 有部分字段 | 不完整、无版本 |
| Chunk | 无，整篇 content | 缺失 |
| Embedding | Qwen 1024 维 | 已有最小实现 |
| Vector Search | pgvector cosine Top-50 | 已有但只针对 global whole Policy |
| BM25/lexical | 无 | 缺失 |
| Metadata Filter | 仅 tenant/status | 不足 |
| Rerank | 无 | 缺失 |
| Context Builder | Prompt 直接拼整篇/结果 | 缺失 |
| Citation | 无 source span | 缺失 |

## 目标 RAG Pipeline

```text
Document
  → Parse
  → Clean
  → Metadata validation
  → Semantic/structural Chunk
  → Embedding
  → Lexical index
  → Metadata Filter
  → BM25 + Vector Search (parallel)
  → Rank fusion
  → Reranker
  → Context Builder
  → structured LLM output
  → Citation Validator
```

### Metadata Schema

每个 PolicyChunk 至少包含：

| 字段 | 类型/要求 |
|---|---|
| source | source ID + source type |
| title | 文档标题 |
| issuer | Authority ID + display name |
| region | normalized region IDs，可多值 |
| industry | normalized industry taxonomy IDs |
| policy_type | controlled enum |
| publish_date | date，未知为 null |
| effective_date | date，未知为 null |
| expiry_date | date，未知为 null；不得假设长期有效 |
| document_id | stable canonical document ID |
| document_version_id | immutable version ID |
| article | 章/节/条/款路径 |
| url | canonical URL |
| chunk_id/span | chunk ID + page/offset |
| content_hash | 检测版本和引用一致性 |
| visibility | global/private + tenant/workspace scope |
| language | zh-CN 等 |

### Parse/Clean

- 保存 original bytes/hash 与 parser version；
- 保留标题、条款编号、表格、附件关系和页码；
- 清理页眉页脚/重复内容，但原始 offset 映射必须保留；
- OCR 结果保存 confidence，不覆盖原文；
- parser/OCR 失败进入结构化状态，不生成空 embedding。

### Chunking

政策优先按章/条/款和表格结构切分，不使用固定字符窗作为唯一策略。Chunk 需要 parent/neighbor IDs；过长条款再做 token-aware 子块，并保留 article path。

企业材料按文档类型使用不同策略：财务表格、证书、知识产权清单、人员表和叙述文档不能共用一个 chunker。

### Hybrid Retrieval

建议执行：

1. query normalization + intent/schema extraction；
2. tenant/workspace/visibility/date/region/type metadata pre-filter；
3. BM25 lexical search 与 pgvector ANN 并行；
4. 使用 Reciprocal Rank Fusion 合并，不把不可比较的原始分数直接相加；
5. cross-encoder/LLM reranker 只重排有限候选并记录版本/成本；
6. Context Builder 做去重、邻块补全、token budget 和 source diversity；
7. LLM 只引用 selected chunk IDs；
8. Citation Validator 检查每个 claim 的 exact span。

当前 PostgreSQL `ts_rank` 不应被标成 BM25。实现阶段应明确选择：

- 小规模基线：PostgreSQL FTS + pgvector，诚实标为 lexical + vector；
- 目标 BM25：OpenSearch/Elasticsearch 或经验证的 PostgreSQL BM25 扩展；
- 通过同一 RetrievalBackend 接口切换，并用 eval 决定，不凭架构偏好增加基础设施。

### Retrieval Contract

```python
class RetrievalHit(BaseModel):
    chunk_id: UUID
    document_version_id: UUID
    article: str | None
    quote: str
    url: str
    lexical_rank: int | None
    vector_rank: int | None
    fusion_score: float
    rerank_score: float | None
    metadata: PolicyChunkMetadata

class RetrievalSnapshot(BaseModel):
    query: str
    filters: RetrievalFilters
    index_versions: dict[str, str]
    hits: list[RetrievalHit]
    selected_chunk_ids: list[UUID]
```

## Citation

生成输出采用 claim-level citation：

```python
class CitedClaim(BaseModel):
    claim_id: str
    text: str
    citation_ids: list[UUID]
    confidence: float

class CitationRecord(BaseModel):
    evidence_id: UUID
    document_version_id: UUID
    chunk_id: UUID
    quote: str
    article: str | None
    page: int | None
    start_offset: int
    end_offset: int
    url: str
```

Citation Accuracy 必须检查引用是否真的支持 claim，不只检查“有 citation ID”。

## Structured Policy Layer

### 不需要先上图数据库

当前规模建议先用 PostgreSQL 的版本化关系模型表达知识图谱。图数据库只有在多跳关系查询、数据规模和团队运维能力证明必要时再引入。

### 核心节点

```text
Policy / Program
EligibilityRule
RequiredMaterial
Benefit
Deadline
Region
Industry
CompanyType
Authority
```

### 关系

```text
PolicyVersion has_rule EligibilityRuleVersion
PolicyVersion requires RequiredMaterialVersion
PolicyVersion offers BenefitVersion
PolicyVersion issued_by Authority
PolicyVersion applies_to Region
PolicyVersion targets Industry
PolicyVersion targets CompanyType
PolicyVersion belongs_to Program
PolicyVersion has_deadline Deadline
```

每条关系保存 source span、confidence、extractor、verification status 和 version。LLM 可提出 relation candidate，但只有 schema/rule validation 和必要人工批准后才能发布。

### EligibilityRule DSL

```python
class EligibilityRule(BaseModel):
    rule_id: UUID
    version: int
    field: CompanyFactType
    operator: Literal[
        "eq", "neq", "gt", "gte", "lt", "lte",
        "in", "contains", "exists", "date_before", "date_after",
        "all_of", "any_of", "not"
    ]
    expected_value: JsonValue
    unit: str | None
    time_window: TimeWindow | None
    blocking: bool
    source_span_id: UUID
    effective_from: date | None
    effective_until: date | None
```

组合规则显式建 RuleGroup；单位、币种、百分比和日期使用 typed normalizer。无法解析的条款进入 manual/unparsed queue，并在 Eligibility 中导致 `NEED_MORE_INFORMATION`，不得由 LLM 自行补齐。

### RequiredMaterial / Benefit / Deadline

- RequiredMaterial：名称、材料类型、必需/条件必需、适用规则、格式、签章/审计要求、source span；
- Benefit：资金/税收/资质/资源类型、金额/比例公式、上下限、币种、支付条件；
- Deadline：申请窗口、rolling/fixed、timezone、补正期限、状态；
- Region/Industry/CompanyType 使用受控 taxonomy 和 alias mapping，不只存自由字符串。

## Eval System 当前状态

- `yance-ai/evals/golden_cases` 只有 2 条简单 schema case；
- runner 不执行模型或引擎，只验证 required keys；README 对“output contract”描述高于实际能力；
- benchmark 16 例包含真实 model answer 和指标，是可复用种子，但不足以支撑发布；
- 评分器使用个人绝对路径，缺失/错误 case 会从分母排除，可能使结果不可比较；
- 没有 retrieval、citation、document generation 专项集；
- 没有统一 EvalRun/EvalCaseResult、数据集版本、成本和 Dashboard。

## `/evals` 目标结构

建议单一 canonical 根目录，业务代码通过 package/CLI 引用：

```text
evals/
  schemas/
    case.py
    result.py
    score.py
  datasets/
    policy_retrieval_eval/
    eligibility_eval/
    citation_eval/
    hallucination_eval/
    document_generation_eval/
  runners/
    retrieval.py
    eligibility.py
    citation.py
    hallucination.py
    document_generation.py
  scorers/
    deterministic.py
    rubric.py
    judge.py
  reports/
  README.md
```

真实客户资料不得直接进入 eval；使用脱敏、合成和经授权样本，并保留 dataset card。

## Eval 数据 Contract

每类 Eval 共同字段：

```python
class EvalCase(BaseModel):
    case_id: str
    eval_type: EvalType
    question: str
    input: dict[str, JsonValue]
    ground_truth: dict[str, JsonValue]
    expected_evidence: list[EvidenceExpectation]
    tags: list[str]
    risk_tier: str
    reference_date: date | None
    dataset_version: str

class EvalCaseResult(BaseModel):
    case_id: str
    model_answer: dict[str, JsonValue] | None
    score: EvalScore
    evidence: list[EvidenceResult]
    error_types: list[EvalErrorType]
    latency_ms: int | None
    cost_amount: Decimal | None
    run_id: UUID | None
```

六个评分维度：

- Correctness：结论/字段与 Ground Truth；
- Completeness：必答条件/字段覆盖；
- Evidence：关键结论是否有支持证据；
- Citation Accuracy：引用是否精确支持 claim；
- Hallucination：无来源事实/数字/材料；
- Actionability：下一步是否具体、可执行、符合状态。

每项分数保存 scorer/version 和原始依据。Judge-model 只能作为一个 scorer，并需用 human-labeled calibration set 验证；不能让同一模型既答题又无校准地自评。

## 五类 Eval

### policy_retrieval_eval

输入 query/profile/filter，Ground Truth 是 relevant ProgramVersion/Chunk IDs。指标：Recall@k、Precision@k、MRR、nDCG、metadata filter accuracy、source freshness。

### eligibility_eval

输入 frozen ProfileVersion + ProgramVersion + RuleVersion，Ground Truth 是逐规则 result 和四态 overall。指标：accuracy、hard-gate recall、严重 false positive、coverage、calibration。

### citation_eval

输入 claims + citations，Ground Truth 是 supporting spans。指标：citation precision/recall、exact span、unsupported claim rate、stale source rate。

### hallucination_eval

包含不存在数字、相近子串、冲突资料、prompt injection、过期政策和诱导补全。指标：hallucination rate、blocked rate、unsafe completion rate。

### document_generation_eval

输入 approved facts + template，Ground Truth 是 required fields/sections/constraints。指标：schema validity、field completeness、fact consistency、citation coverage、format validity、actionability 和 human major-edit rate。

## Eval 真实性规则

1. 只有实际执行的 case 进入分母；但 missing/error 必须单独计入 run completion/error rate，不能静默排除。
2. Dashboard 默认查询持久化 EvalRun；没有成功结果时显示 **“No evaluation data yet.”**。
3. Seed/demo 数据必须 `is_demo=true`，默认 Dashboard 过滤，不进入融资指标。
4. 每个图表显示 dataset version、engine/model/prompt/index version、sample size、run time 和 error count。
5. 不以 2 条 schema case 或 16 条 benchmark 推断总体生产质量。
6. 修改数据集/Gold/评分器必须新版本，不能覆盖历史结果。
7. 失败 case、timeout 和 parse error 不得通过删文件改善 Pass Rate。

## Eval 数据模型

```text
EvalDataset
EvalDatasetVersion
EvalCase
EvalRun
EvalCaseResult
EvalDimensionScore
EvalEvidenceResult
EvalError
EvalComparison
```

EvalRun 保存 target workflow/agent/model/prompt/index/rule/template versions、status、case counts、latency/cost totals 和 created_by。CaseResult 可关联生产同构 AgentRun，保证离线/线上使用同一 Harness。

## Admin Eval Dashboard

### 卡片

- Accuracy；
- Citation Accuracy；
- Hallucination Rate；
- Pass Rate；
- Average Latency；
- Average Cost。

### 必要上下文

- Eval 类型、dataset/version、sample size；
- model/prompt/agent/rule/index version filters；
- overall 与 risk/tag/policy type 分桶；
- error/timeout count；
- 与上一已冻结 baseline 的差异；
- 可下钻 Question、Ground Truth、Model Answer、Score、Evidence、Error Type。

### 空状态

数据库没有真实 EvalRun 结果时，六张卡不能显示 0%、100% 或样例数字，统一显示：

> No evaluation data yet.

可以提供“Run evaluation”操作，但不能自动创建好看的种子结果。

## Observability 指标

Agent Dashboard 和 Eval Dashboard 分开：前者监控生产执行，后者衡量质量。共同维度包括 workflow/agent/model/prompt/version/tenant（受权限限制）。

生产指标：run success、queue delay、step latency、tool errors、retry、human review time、tokens、cost、artifact approval。质量指标只来自 Evaluation，不用任务 completed 状态代替 correctness。

## 实施顺序

### P0

- 修 Eligibility blocking/Evidence validator/PDF/tenant P0；
- 关键结果未 Verification/Human Review 前不允许 completed/ELIGIBLE/final artifact。

### P1-A：Harness Foundation

- versioned Agent/Workflow/Prompt/Tool/Schema registry；
- AgentRun/Step/ToolCall/Evidence/Artifact/Evaluation/Error/Retry migration；
- durable queue、lease、idempotency/outbox；
- 状态机和 trace API/Admin 只读页。

### P1-B：RAG Foundation

- Source/Document/Version/Chunk/Span 和完整 metadata；
- Parse/Clean/Chunk/Embedding/lexical indexes；
- hybrid retrieval、fusion、rerank、Context Builder、Citation Validator。

### P1-C：Policy Layer

- Program/Rule/Material/Benefit/Deadline/Authority/taxonomy；
- typed DSL、source relations、publication/review workflow；
- EligibilityAgent 只消费已发布规则版本。

### P1-D：Workers + Verified Loop

- 先实现 DocumentAnalysis、CompanyProfile、PolicySearch、Eligibility、Evidence；
- 再实现 Application、Report；
- QA/verifiers 与每个 Worker 同时交付，不留到最后。

### P1-E：Real Evals

- canonical `/evals`、五类 runner、真实 Harness 执行；
- 100–300 条冻结分桶集；
- Admin Eval Dashboard 和 CI release Gate。

## 验收标准

### Harness

- 任一 AgentRun 可查看 plan、steps、tool calls、evidence、artifacts、evaluations、errors、retries、cost；
- worker kill/restart 可恢复，不重复 Tool side effect；
- 非法状态转换和跨租户 resource ref 被拒绝；
- schema-invalid output 不能 completed。

### Loop

- 每个 critical workflow 至少一个 deterministic verifier；
- Eligibility 必须经过 Eligibility → Evidence → QA/Verifier → Final Gate；
- verifier fail 后只可 retry/review/fail。

### RAG

- 所有选中 context 可回到 immutable document version/span；
- metadata/ACL 在检索前强制；
- lexical/vector/fusion/rerank 分数和版本可追踪；
- claim-level citation validator 通过后才能输出关键结论。

### Policy Layer

- 所有 blocking rule 有 typed DSL 或明确 unparsed 状态；
- Rule/Material/Benefit/Deadline 绑定 source span；
- policy 更新创建新版本并触发受影响 assessment 重评。

### Eval

- 五类 Eval runner 实际运行产品代码；
- Dashboard 无数据时显示 `No evaluation data yet.`；
- 结果展示 sample/version/error/cost，demo 结果不进入正式指标；
- CI 以冻结 baseline 和风险分桶 Gate 阻止回归。

## 可复用与应替换

### 可复用

- FastAPI/Pydantic/SQLAlchemy/PostgreSQL/pgvector 技术栈；
- LLM Provider adapters 的基础连接代码；
- Policy Engine 的部分结构化 schema、确定性 normalizer 和保守 fallback；
- AgentRun 名称和 benchmark 透明报告作为迁移种子。

### 应替换/重构

- 客户端可写 AgentRun API；
- Web BackgroundTasks 长任务；
- 路由内直接 LLM 调用；
- whole-policy single embedding；
- 自由 `PolicyRule.rule_json` 作为唯一结构层；
- 只验 JSON key 的 eval runner；
- 硬编码 quality score、latency 和模型 fallback 作为真实观测值。
