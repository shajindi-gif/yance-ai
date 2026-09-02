# Yance.ai 升级路线图

> 阶段编号说明：用户确认的正式执行序列为 Phase 0–11，详见 `14_PHASED_IMPLEMENTATION_PLAN.md`。本文保留 12 周/6 个月的产品成熟度视角，不再作为 Git commit 或工程 Gate 的阶段编号依据。

## 路线图原则

目标不是重写，也不是优先改首页。保留 Next.js、FastAPI、PostgreSQL/pgvector 和模块化单体，按风险 Gate 修复，再完成一个可销售的垂直闭环。

建议以 12 周为第一个融资级里程碑，之后 3–6 个月扩展平台能力。日期从开发正式启动日计算；本轮仅完成审计文档，没有修改业务代码。

## 成功定义

12 周结束时，演示必须能使用一个脱敏真实企业完成：

**导入资料 → 版本化企业画像 → 扫描版本化政策 → 逐条件证据判断 → 材料缺口 → 任务/负责人/截止日 → 生成申报初稿 → 人工审批 → 可追溯交付 → 持续重评。**

完整范围以 `11_AGENT_WORKFLOW_AUDIT.md` 的 14 步 Golden Journey 为产品验收主线；任何阶段性 UI 都不能替代其中的数据对象、状态机、证据和负向测试。

同时满足：P0=0、根级 CI 绿灯、生产可回滚、跨租户测试通过、关键 AI 指标达到发布 Gate、支付和权益可对账、所有公开声明有证据。

## Phase 0：生产止血与基线（第 0–2 周）

### Outcomes

- 不再存在可直接伪造付款/权益的生产入口；
- 标准数据库 schema 可运行 Task/Deliverable；
- 所有 P0 有 Owner、测试和退出条件；
- 对外页面不再声称未实现的安全和产品能力。

### Deliverables

| Workstream | 交付 | 验收 |
|---|---|---|
| Commerce | production 移除 demo-pay/task-pay；订单服务端定价；禁用坏的银行/发票路径 | 未付款用户无法下载；负向测试 |
| Data | forward migration 对齐 Task/Deliverable | base→head + CRUD smoke + schema diff |
| Tenant | platform admin 与 tenant role 设计；修正 admin 路由/policy scope | cross-tenant matrix |
| AI Safety | 修 blocking/evidence numeric；自动 ELIGIBLE 加人审 Gate | 回归集覆盖事故/环保/信用/数字边界 |
| PDF | HTML escape、禁 URL fetch、renderer sandbox 方案 | SSRF/LFI payload 测试 |
| Truth | 安全/隐私/下载/定价/条款逐条修正 | claim-control register 签核 |
| CI | 把 workflows 移到根 `.github/workflows`；backend/frontend 基础 build | required checks 在 PR 实际运行 |

### 不做

- 不拆微服务；
- 不新增移动端/浏览器插件；
- 不做大规模 UI 重设计；
- 不在 P0 未清零时接真实客户敏感资料。

## Phase 1：可信基础设施（第 3–5 周）

### Outcomes

- 租户、任务、支付和部署可在失败/重试下保持一致；
- 有 staging、可观测性和可恢复备份；
- 前后端 contract 由机器验证。

### Deliverables

1. **Identity/Tenant**
   - 同源安全 session、login shared rate limit、password reset/email verification；
   - Tenant active、邀请、role matrix；
   - tenant repository + 首批 RLS policies。

2. **Durable Workflow**
   - Redis/managed queue 或等价持久执行框架；
   - WorkflowRun/StepRun/Attempt、lease、retry、dead-letter、cancel；
   - transactional outbox 和 idempotency keys。
   - 按 `12_AGENT_ARCHITECTURE_RAG_EVAL_SPEC.md` 建立 AgentRun/AgentStep/ToolCall/Evidence/Artifact/Evaluation/Error/Retry 和统一状态机；
   - 先交付只读 Agent Trace Admin，确保后续 Worker 的执行证据从第一天可见。

3. **Commerce ledger**
   - Product/PriceVersion、OrderLine、ProviderEvent；
   - 支付宝/Stripe sandbox webhook 完整校验、幂等、Entitlement 原子发放；
   - refund/revocation 和每日 reconciliation skeleton。

4. **Observability**
   - OpenTelemetry traces、API/queue/model/payment metrics、error aggregation；
   - tenant/user 使用受控标识，敏感正文脱敏；
   - dashboard、alerts、SLO 和 on-call runbook。

5. **Delivery**
   - root CI：ruff/pytest/migration/eval、frontend lint/type/build/unit/e2e、image/SCA/secret scan；
   - staging + IaC + immutable image + rollback；
   - 自动备份和首次 restore drill。

### Gate

- P0=0；
- 所有核心 API own/other tenant 测试通过；
- webhook replay 10 次只产生一个权益；
- worker kill/restart 后任务恢复；
- staging restore 达到声明的 RPO/RTO。

## Phase 2：Evidence-First Golden Journey（第 6–9 周）

### Outcomes

- 产品从“输入问题→回答/PDF”升级为“资料→证据→判断→任务”。

### Deliverables

1. **Document ingestion**
   - quarantine upload、大小/MIME/magic/malware；
   - OCR/parser sandbox；
   - DocumentVersion/ParseRun/Chunk/Span；
   - UI 展示解析状态和错误。

2. **Company Profile v1**
   - typed facts、unit、effective date、source span、confidence；
   - profile completeness、冲突和用户确认；
   - immutable CompanyProfileVersion。

3. **Policy Knowledge v1**
   - PolicySource/Document/Version/Chunk/Criterion；
   - global published + tenant private visibility；
   - hybrid retrieval、metadata filter、citation；
   - policy update/freshness 状态。

4. **Decision v1**
   - 分离 relevance、eligibility、evidence coverage、confidence；
   - CriterionResult 双向引用 policy span/company fact；
   - DecisionSnapshot 固定 profile/policy/engine/model/prompt version；
   - human approve/reject/edit。

5. **App UX**
   - marketing/app layouts；
   - Company evidence viewer、Opportunity detail、Case workspace；
   - materials/tasks/owner/deadline/activity/approval。

6. **Agent/RAG Harness**
   - Orchestrator + 首批 DocumentAnalysis/CompanyProfile/PolicySearch/Eligibility/Evidence Workers；
   - Plan→Retrieve→Reason→Act→Verify→Retry→Finish；
   - lexical/vector fusion、rerank、Context Builder 和 claim-level Citation。

### Gate

- 三个脱敏企业完成从上传到人审判断；
- 关键结论 100% 有 policy citation，企业事实有 source 或明确 user-asserted；
- 跨租户 retrieval=0 泄漏；
- 无 evidence 时不会输出确定性满足。

## Phase 3：申报执行与评测（第 10–12 周）

### Outcomes

- 系统生成真实可审阅申报初稿和交付包；
- AI 质量可量化并作为发布 Gate。

### Deliverables

- versioned application templates 和字段映射；
- Draft workflow：outline → field fill → citation validate → policy validate → human approval；
- DeliverableVersion、diff、comment、revision、accept；
- 通知、截止日和失败升级；
- 真正 eval runner，冻结 100–300 条分桶数据；
- retrieval/citation/eligibility/draft/workflow/security 指标；
- Model Gateway：retry、budget、quota、redaction、provider policy、cost ledger；
- 3 个真实试点的时间成本、人工修改和交付验收数据。

### 发布 Gate

| 指标 | Gate |
|---|---:|
| Hard-gate recall | ≥95% |
| 严重假阳性 | ≤2% |
| Overall eligibility accuracy | ≥85%，按类型分桶 |
| Retrieval recall@10 | ≥95% |
| Citation precision | ≥98% |
| Structured output | ≥99.5% |
| Task success | ≥99%，失败可恢复 |
| Cross-tenant security | 0 泄漏 |

未达 Gate 的政策类型保持 Beta + 强制专家复核，不用平均数掩盖高风险分桶。

## Phase 4：企业成交能力（第 4–6 个月）

### 产品

- 园区/专业机构 portfolio、多企业批量扫描、顾问席位和白标；
- 订阅/usage/credits、账单、合同和客户成功健康度；
- API keys、webhooks、CRM/OA/ERP integration；
- SSO/SAML/OIDC，视客户需求增加 SCIM；
- 政策变更持续重评和通知偏好。

### 平台

- platform admin：policy publishing、tenant support、failed jobs、model/prompt/template rollout、billing reconciliation；
- RLS 全覆盖、审计搜索、数据导出/删除；
- capacity/load test、成本优化、worker autoscaling；
- 独立渗透测试、供应商/DPA、IR tabletop；
- 99.9% SLA 只有在架构、监控和历史数据支持后再承诺。

## Phase 5：Vertical Agent Infrastructure（6 个月以后）

只有第一个政策申报闭环具有留存和毛利后，才抽象跨 vertical 平台：

- reusable source ingestion/connectors；
- domain schema/criterion/template registry；
- Agent workflow SDK、approval primitives、evidence graph；
- Eval registry、model policy、cost governance；
- tenant knowledge overlays 和 partner marketplace。

避免把尚未验证的业务特性过早抽象为通用 Agent 平台。

## 团队建议

12 周最小稳定团队：

- 1 Staff/Tech Lead：架构、tenant、workflow、release；
- 1 Backend/Data Engineer：schema、ingestion、knowledge/evidence；
- 1 Full-stack Engineer：app UX、API contract、case workspace；
- 1 Applied AI Engineer：policy DSL、RAG、eval/model gateway；
- 0.5 Security/DevOps：IaC、CI、observability、threat model；
- 1 Product/Domain Lead + 政策专家：标注、模板、人审、试点；
- 法务/隐私和财务支付按里程碑介入。

每个 P0/P1 只有一个 DRI；安全、AI 质量和商业完整性需要双人审批。

## 里程碑看板

| 里程碑 | 时间 | 结果指标 |
|---|---|---|
| M0 Safe to develop | 第 2 周 | P0 代码阻断关闭，CI 实际运行 |
| M1 Safe staging | 第 5 周 | tenant/payment/workflow/deploy 可恢复 |
| M2 Evidence product | 第 9 周 | 3 家企业资料到证据判断闭环 |
| M3 Investor-ready pilot | 第 12 周 | 初稿/审批/交付 + eval 达 Gate + 客户验收 |
| M4 Enterprise sellable | 第 6 月 | Admin/SSO/API/portfolio/SLA 证据与续费数据 |

## 决策与范围控制

每两周用同一顺序评审：

1. P0/P1 风险 burn-down；
2. Golden Journey 成功率和人工介入；
3. AI 分桶质量；
4. 客户使用/留存；
5. 单任务成本和毛利；
6. 才讨论新增功能。

任何新 vertical、渠道端或大规模品牌升级，都必须说明它如何改善上述指标，否则进入 backlog。
