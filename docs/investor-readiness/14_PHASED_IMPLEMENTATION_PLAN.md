# Investor-grade Upgrade：Phase 0–11 实施总计划

本计划是正式工程阶段编号。所有 Phase 坚持兼容现有 Next.js、FastAPI、SQLAlchemy、PostgreSQL/pgvector，采用 forward-only 渐进迁移；不重建空项目、不删稳定功能、不用 UI placeholder 冒充后端。

## 每阶段固定协议

每个 Phase 开始前必须提交一份 phase plan，包含：目标、非目标、现状证据、涉及文件、API/数据契约、migration、风险、回滚、测试和手动验收。

每个 Phase 结束必须同时满足：

1. 工作树只包含本阶段授权修改；
2. 新库 base→head 和升级路径可验证，或明确说明本阶段无 migration；
3. lint、typecheck、unit/integration/API/agent/RAG/E2E 中适用项通过；
4. frontend/backend build 和启动 smoke 通过；
5. 手动验收记录实际结果；
6. 生成 changelog；
7. 一个独立、可回滚的 commit；
8. 未通过项不能写成完成，阻断则不进入下一 Phase。

## Phase 0 — Backup + Audit

### 目标

- 固定基线、保护现有代码；
- 完成产品、架构、安全、数据、Agent/RAG/Eval、Enterprise SaaS 审计；
- 建立 P0/P1/P2/P3 风险和正式 Phase 计划。

### 文件

- `docs/investor-readiness/00_CURRENT_STATE.md` 至 `15_PHASE_0_CHANGELOG.md`。

### Migration / Tests / Build

- 无数据库修改；
- 运行现有前后端测试、lint、build、Eval、依赖审计和 migration graph；
- 失败原样记入基线。

### Gate

- backup branch 和 `feature/investor-grade-upgrade` 存在；
- 审计文档可逐项追踪到代码；
- Phase 0 独立 commit；
- 不修改业务代码。

## Phase 1 — P0 Stability & Security

### 目标

先让系统“不能伪造、不能越租户、不会被确定性故障阻断”，再扩功能。

### 主要文件

- Backend：`app/core/config.py`、`security.py`、`api/deps.py`、payments/commerce/tasks/policy_engine/documents routes、PDF/invoice renderer；
- Migrations：Task/Deliverable drift、平台管理员/支付事件所需 additive migration；
- Frontend：checkout/reports/dashboard/security/privacy/downloads；
- Root：`.github/workflows/*`、`SECURITY.md`、受控 `.env.example`。

### 实施

- production 禁用 demo-pay/task-pay；服务端 SKU 定价；支付 webhook 幂等和金额/商户校验；
- 统一 tenant scoped repository，修 admin 路由与 policy ownership；
- 修 Task/Deliverable schema drift；
- HTML escape + restricted URL fetcher；
- 资格硬门槛与 mandatory human review；
- 财务配置移出代码，secret/history scan 与轮换；
- 修正所有无法证明的外部声明；
- root CI 启动 backend/frontend 基线 job。

### 测试与 Gate

- cross-tenant、payment replay、unpaid download、PDF SSRF/LFI、hard-gate regression；
- PostgreSQL base→head + CRUD + ORM diff；
- Ruff/pytest/build/CI 绿灯；
- P0=0 才进入 Phase 2。

## Phase 2 — Design System

### 目标

建立企业级视觉和应用 shell，不改变业务真值。

### 主要文件

- `website/app/(marketing)`、`(auth)`、`(app)`、`(platform-admin)`；
- `website/components/ui`、`website/styles/tokens.css`、字体、icons；
- loading/error/not-found/accessibility 基础组件。

### 实施

- 设计 tokens、表格/表单/Badge/Drawer/Tabs/EmptyState/Skeleton/ErrorState；
- 分离营销与应用布局；实现目标侧边栏；
- Homepage 按 5 秒价值测试重构，社会证明只接真实数据；
- 自托管字体、`next/image`、responsive/a11y/performance budget。

### 测试与 Gate

- component、axe、visual regression、mobile/desktop 手测；
- 页面 CTA 不出现无后端按钮；
- CWV lab baseline 不退化。

## Phase 3 — Core Product Workflow

### 目标

完成 Register → Organization → Company Profile → Document ingest request → Scan request → Opportunity → Application 的持久业务骨架。

### 数据与 API

- Organization/Membership 兼容 Tenant/User；
- CompanyProfile/CompanyProfileVersion/CompanyFact；
- Opportunity snapshot；Application/Requirement/Task/Activity；
- Analytics canonical events。

### 前端

- `/companies`、`/documents`、`/opportunities` 与详情、`/applications/[id]` 基础 tabs；
- Home Dashboard 只显示真实查询和 empty state。

### Gate

- API contract 自动生成/检查；
- Register/Create Company/Create Application 集成测试；
- 主流程 E2E 先覆盖不含 AI 的持久状态转换。

## Phase 4 — Agent Harness

### 目标

实现统一 Orchestrator、Agent contracts、Run/Step/Tool/Evidence/Artifact/Error/Retry 和持久队列。

### 数据与服务

- Agent、AgentRun、AgentStep、ToolCall、AgentError、RetryAttempt；
- Workflow/WorkflowRun、lease、idempotency、cancel、outbox/dead-letter；
- Model Gateway 的 chat/structured_output/embedding 兼容接口；
- `/admin/agent-runs` 只读 trace。

### Gate

- Plan→Retrieve→Reason→Act→Verify→Retry→Finish 状态测试；
- worker kill/restart 可恢复；
- verifier fail 不能 completed；
- run_id/request_id/tenant_id trace 完整且无敏感正文。

## Phase 5 — RAG + Evidence

### 目标

建立 DocumentVersion→Parse→Chunk/Span→Embedding→Hybrid→Rerank→Context→Citation 和 Structured Policy Layer。

### 数据

- DocumentVersion/ParseRun/DocumentChunk/SourceSpan；
- PolicySource/PolicyVersion/EligibilityRuleVersion；
- RequiredMaterial/Benefit/Deadline/Authority/Region/Industry relations；
- RetrievalRun/RetrievalHit/Evidence/Citation。

### Gate

- 文件 quarantine/magic/MIME/malware/parser sandbox；
- lexical + vector + metadata + rerank 可复现；
- 所有关键 claim 有 exact source span；
- cross-tenant retrieval 0 泄漏；
- 无证据不输出确定性资格。

## Phase 6 — Application Workspace

### 目标

交付 Overview、Requirements、Documents、Generated、Tasks、Evidence、Activity 与右侧 Agent Panel。

### 数据与功能

- ArtifactVersion、TemplateVersion、Approval、Comment、Revision；
- materials gap、task dependency、assignee、deadline；
- Ask/Generate/Check/Fix/Explain 对应真实 workflow command；
- DOCX/PDF/XLSX/JSON 导出、hash、版本和审阅。

### Gate

- Approve/Reject/Edit/Regenerate 全部可审计；
- 下载只允许已授权 artifact；
- Application 主流程 E2E 完整通过。

## Phase 7 — Admin + Analytics

### 目标

交付平台运营面与真实事件系统。

### 页面

- Users、Organizations、Companies、Agent/Workflow Runs、LLM Usage/Costs；
- Documents、Policies、Errors、Feedback、System Health；
- `/admin/investor-metrics`。

### 数据与 Gate

- event registry/schema version/idempotency/retention；
- metrics 明确定义时间窗和排除 Demo；
- platform admin MFA/reason/audit；
- Revenue/Paying Customer 不从 demo/未验证订单产生。

## Phase 8 — Eval

### 目标

真实运行五类 Eval 并形成 release gate。

### 范围

- policy retrieval、eligibility、citation、hallucination、document generation；
- EvalDataset/Case/Run/Result、judge version、人审和 error taxonomy；
- Admin dashboard：Accuracy、Citation Accuracy、Hallucination Rate、Pass Rate、Latency、Cost。

### Gate

- 没有数据严格显示 `No evaluation data yet.`；
- 分母包含失败，禁止跳过污染；
- 质量数据链接 dataset/model/prompt/policy/profile snapshot；
- 发布阈值按高风险分桶，不用总体平均掩盖严重假阳性。

## Phase 9 — Billing + Enterprise

### 目标

Free/Pro/Business/Enterprise 与 Organization、RBAC、Usage、Quota、Invoice、Subscription 真实闭环。

### 数据

- Plan/PriceVersion/Subscription/Item；
- UsageMeter/Record/Budget；
- ApiKey、RetentionPolicy、ExportJob、DeletionRequest；
- enterprise entitlement 与 optional SSO/MFA policy。

### Gate

- webhook replay/退款/降级/宽限/取消/对账；
- per user/org/workflow budget；
- delete/export/retention 可演练；
- 套餐展示与服务端 entitlement 完全一致。

## Phase 10 — Demo + Data Room

### 目标

建立明确隔离的 Investor Demo 和由真实实现生成的数据室材料。

### 文件与页面

- `/demo`：3–5 个带 DEMO badge 的企业案例；
- `/docs/data-room/` 十二份指定材料；
- `DEMO_SCRIPT.md`：3/7/15 分钟；
- metrics 页面仅管理员访问。

### Gate

- 3–5 分钟跑完画像→扫描→资格→证据→Application→文档；
- Demo 数据永不进入收入/活跃/质量指标；
- 每份 data-room 声明有代码、测试或运行证据，未来态明确标注。

## Phase 11 — Testing + Production Hardening

### 目标

把完整产品变成可部署、可恢复、可监控、可回滚的 release candidate。

### 范围

- unit/integration/API/agent/RAG/E2E/security/performance/load；
- GitHub Actions：lint/typecheck/test/build/security/migration；
- staging、immutable image、SBOM、SAST/SCA/secret/container scan；
- OpenTelemetry、alerts、SLO、backup restore、incident/rollback runbook；
- Golden Journey browser + API + worker 全链验收。

### 最终 Gate

- broken build 无法 merge；
- 从零迁移、升级、rollback/restore 演练通过；
- Investor Demo 全程真实可运行；
- Admin 可查看 Agent trace、metrics、Eval；
- P0=0，P1 有 owner/date/accepted risk；
- 生成 `INVESTOR_READY_REPORT.md` 和最终 `DEMO_SCRIPT.md`。

## Commit 约定

每 Phase 至少一个独立 commit，示例：

```text
docs(audit): establish investor-grade phase zero baseline
fix(security): close production payment and tenant isolation blockers
feat(design): introduce enterprise application design system
feat(workflow): persist company-to-application workflow
feat(agent): introduce agent execution harness
feat(rag): add evidence-first hybrid retrieval
feat(workspace): build application workspace
feat(admin): add agent operations and metrics dashboards
feat(eval): run evidence-grounded quality evaluations
feat(billing): enforce subscription usage and quotas
feat(demo): add isolated investor demo and data room
test(e2e): cover end-to-end policy workflow
```

禁止 squash 掩盖 migration 或安全修复历史；若一个 Phase 过大，按垂直可运行切片拆 commit，但 Phase Gate 只在全部切片通过后关闭。
