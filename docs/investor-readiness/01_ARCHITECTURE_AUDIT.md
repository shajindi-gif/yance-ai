# 架构审计

## 当前逻辑架构

```text
Browser
  └─ Next.js 14 App Router
       ├─ 营销页 / 法务页 / 下载页
       ├─ client-side 登录与工作台
       └─ localStorage JWT → NEXT_PUBLIC_API_URL

FastAPI /api/v1
  ├─ auth / tenants / companies / documents
  ├─ policies / reports / policy-engine
  ├─ tasks / deliverables / applications
  ├─ orders / payments / invoices / entitlements
  └─ analytics-events / agent-runs

Service layer
  ├─ Qwen/DeepSeek/OpenAI-compatible/Anthropic adapters
  ├─ whole-policy pgvector retrieval
  ├─ deterministic + LLM policy evaluator
  ├─ WeasyPrint report/invoice rendering
  └─ OSS presigned upload

PostgreSQL 16 + pgvector / OSS / external LLM and payment providers
```

这个形态属于模块化单体的早期版本。对天使轮团队而言，继续使用模块化单体是合理选择；当前不需要拆微服务。真正需要的是明确领域边界、持久工作流、统一租户 scope、数据版本与可观测性。

## Repo 与构建边界

### 现状

- 根目录同时容纳 `website/`、`yance-ai/` 和 `benchmark/`，但没有根级 workspace、统一 Makefile、根级 CI 或版本发布约定。
- 后端自己的 `.github/workflows` 位于 `yance-ai/.github/workflows/`。以当前父目录为 Git 仓库根时，GitHub 不会把嵌套目录识别为工作流，因此现有 CI/CD 实际上不会触发。
- 前端 `package.json:5-9` 只有 dev/build/start，没有 lint、typecheck、test、e2e。
- 前端 Dockerfile 复制 `.next/standalone`，而 `next.config.js` 没有 `output: 'standalone'`，容器构建路径不成立。
- 后端版本为 0.1.0；生产手册写 v0.2.0；报告、页面和仓库没有单一 release version。

### 风险

| 优先级 | 问题 | 影响 |
|---|---|---|
| P1 | 嵌套 CI 无效 | PR 可以在没有测试、lint、迁移验证和镜像构建的情况下合并 |
| P1 | 前端 Docker 配置不一致 | 标准容器发布失败，环境只能依赖人工步骤 |
| P1 | 根目录没有统一 build/release contract | 无法证明某次测试、镜像、迁移和生产版本属于同一 commit |
| P2 | 文档和运行架构存在 Mac、ECS/RDS、腾讯云香港三套叙述 | 工程尽调无法确认真实拓扑、数据地域和故障域 |

## 模块边界审计

| 边界 | 当前实现 | 主要缺口 | 评级 |
|---|---|---|---|
| Identity & Tenant | JWT + UserRole + tenant_id | 无 platform admin、session、MFA、SCIM/SSO、RLS | P0/P1 |
| Enterprise Profile | Company + metadata_json | 无 schema/version/provenance/completeness/conflict resolution | P1 |
| Policy Knowledge | Policy + PolicyRule + embedding | global/tenant 语义冲突；无 source version/chunk/citation | P0/P1 |
| Opportunity | Opportunity + evidence_json | 重复写入、无唯一快照、不是资格结论 | P1 |
| Case/Application | Application | 只有 CRUD 数据对象，无真实 case 状态机和材料映射 | P1 |
| Agent Work | Task/Deliverable/Revision/AgentRun | 迁移漂移、非持久执行、同一假管线复用所有任务 | P0/P1 |
| Commerce | Product/Order/Payment/Entitlement/Invoice | 可伪造支付、定价不可信、真实回调不授予权益 | P0 |
| Evidence/Eval | evaluator + benchmark | 样本小、CI eval 不运行引擎、线上决策无版本快照 | P0/P1 |
| Observability | logs/events/runs | 无 trace/metric/SLO/alert/cost lineage | P1 |

## 关键耦合和架构异味

1. 路由直接承担领域逻辑、事务和第三方调用。例如报告路由同时做 embedding、查询、Prompt 组装和 LLM 调用，支付路由直接操作订单状态。
2. `demo_match.py` 将创业演示、产品目录、支付、分析、报告和下载权限揉在同一文件，并被生产 router 无条件加载。
3. `tasks.py` 将 API、worker、AgentRun、匹配、PDF、交付和商业状态放在同一进程；进程重启即丢失工作。
4. tenant filter 分散在每个查询里，无法通过类型或基础设施保证；少写一个条件就跨租户。
5. JSON 被用于画像、证据、表单、运行 metadata、分析属性和支付 raw response，但缺少版本、schema registry 和敏感字段分类。
6. 全局政策与租户数据没有明确的 ownership/visibility 模型：matcher 只读 global，CRUD 和语义搜索只读当前 tenant，workflow 又要求 policy 属于 tenant。
7. 生成式输出、检索证据、业务状态和支付权益没有统一的事件/版本关联，无法复现“某报告为何在某时刻得出该结论”。

## 建议目标架构：模块化单体 + 持久工作流

```text
Web / Partner API
       │
Identity Gateway ── tenant context / session / rate limit / audit
       │
Application API (modular monolith)
  ├─ Profile Context       ├─ Policy Knowledge
  ├─ Opportunity/Evidence  ├─ Case & Application
  ├─ Commerce              └─ Admin/Governance
       │                         │
       ├─ transactional outbox ─┤
       ▼                         ▼
Durable Workflow / Queue    Postgres + RLS
  ├─ ingest_document        ├─ source/version/chunk
  ├─ scan_opportunities     ├─ evidence/decision snapshot
  ├─ evaluate_eligibility   ├─ task/deliverable/revision
  ├─ draft_application      └─ order/payment/entitlement ledger
  └─ human_review
       │
Model Gateway / Retrieval / Eval / Trace
       │
OSS, OCR, LLM providers, payment providers, notifications
```

### 关键设计原则

- **不拆微服务**：先按 Python package/domain service 分模块，事务边界清晰后再根据负载拆分。
- **租户上下文默认安全**：统一 repository/query helper，加 PostgreSQL RLS；platform admin 使用独立身份和显式 break-glass 审计。
- **工作必须可恢复**：HTTP 只创建任务，worker 通过队列消费；使用 lease、idempotency key、retry policy、dead-letter 和 cancellation。
- **每个结论可复现**：保存 company profile version、policy version、retrieval snapshot、prompt/model、规则版本、evidence spans 和 evaluator version。
- **支付是账本，不是布尔值**：订单、支付尝试、provider event、entitlement、refund 分离，状态变化原子且幂等。
- **控制面与数据面分离**：平台 Admin 管理政策发布、模型、模板、租户和风控；租户 Admin 管理成员、企业、权限和账单。

## 架构决策建议

| ADR | 决策 | 理由 | 优先级 |
|---|---|---|---|
| ADR-002 | 全局政策是 platform-owned，租户可叠加 private knowledge；读取规则为 global published + own private | 消除当前 global/tenant 冲突 | P0 |
| ADR-003 | 引入持久队列和 outbox；任务 API 不直接执行 | 保证可恢复、可重试、可观测 | P1 |
| ADR-004 | PostgreSQL RLS + application tenant context 双层隔离 | 降低手写 filter 遗漏风险 | P1 |
| ADR-005 | 证据/决策采用 immutable snapshot + version | 支撑审计、复现和客户争议处理 | P1 |
| ADR-006 | 支付以 provider event ledger 驱动 entitlement | 防重复、伪造和部分提交 | P0 |
| ADR-007 | 所有 LLM 经 Model Gateway，统一重试、预算、脱敏、trace、policy | 让 AI 成本和风险可治理 | P1 |
| ADR-008 | 营销站与登录后应用使用独立 layouts | 降低耦合，改善安全和 SaaS 信息架构 | P2 |

## 非功能性目标

首个可销售版本建议明确以下 SLO，而不是笼统说“企业级”：

- API 月可用性：99.5%，核心读请求 p95 < 800 ms（不含外部 LLM）。
- Agent 任务：创建成功率 > 99.5%，可恢复率 100%，成功/失败状态最终一致。
- 跨租户泄露：0；安全回归套件为发布硬 Gate。
- 支付事件：幂等重复处理无副作用；每日自动对账差异可见。
- 资格判断：按政策类型分桶发布阈值；硬门槛 recall ≥95%、严重假阳性 ≤2%，未达标强制人工复核。
- RAG 引用：关键结论 100% 绑定政策版本和页/段证据；无证据则输出“不足”。
- RPO/RTO：初期 RPO 24 小时、RTO 4 小时；完成演练后才能公开声明。

## 架构修复顺序

1. P0 schema/payment/tenant/PDF/AI Gate；
2. 根级 CI、干净环境迁移验证、前端 build；
3. 模块化 domain service、统一 tenant scope、支付账本；
4. durable workflow + ingestion pipeline；
5. evidence snapshot、eval registry、model gateway；
6. RLS、platform admin、observability/SLO；
7. 在真实负载和组织边界出现后再讨论服务拆分。
