# 数据模型审计

## 结论

数据模型覆盖了 Vertical AI SaaS 的多数名词，但仍是“对象清单”，不是可验证的业务账本。最紧急问题是 ORM 与 migration 已经漂移；更深层问题是画像、政策、证据、判断、工作流和支付都缺少版本与不可变事件，导致系统无法复现历史结论或可靠审计。

## 当前核心实体

| 域 | 实体 | 当前作用 | 主要问题 |
|---|---|---|---|
| Identity | Tenant, User | 组织、成员、角色 | 无 membership、多组织、邀请、session、platform admin |
| Profile | Company, Document | 企业基础字段、上传对象 | 画像塞 JSON；无来源/版本/验证；文档未摄取 |
| Knowledge | Policy, PolicyRule | 政策与规则、whole embedding | global/tenant 语义冲突；无版本/chunk/source |
| Decision | Opportunity, Application | 匹配结果、申报对象 | 无唯一快照、decision/evidence model、状态约束 |
| Commerce | Product, Order, Payment, Invoice, Entitlement | SKU、订单、支付、权益 | 非账本；价格和状态可伪造；缺退款/订阅/usage |
| Execution | Task, Deliverable, RevisionRequest, AgentRun | Agent 任务与交付 | migration 漂移；无 step/attempt/approval/lease |
| Governance | AuditLog, AnalyticsEvent | 审计、分析 | AuditLog 未使用；事件 schema 和可信度不明 |

## P0：Migration/ORM 漂移

### Task

- ORM 有 `progress`、`current_stage`（`models.py:305-306`）；迁移 0008 无这两列。
- 迁移有 `metadata`（`20260817_0008_task_deliverable.py:38`）；ORM 无此属性。
- task API 和 worker 高频读取/写入缺失列，因此标准 `alembic upgrade head` 后运行会失败。

### Deliverable

- ORM 继承 `TimestampMixin`，查询期望 `created_at/updated_at`。
- 迁移没有这两列，只有 `generated_at/delivered_at/accepted_at`；另有 ORM 不知道的 `metadata`。

### 其他漂移风险

- migration server defaults 与 ORM Python defaults 并不总一致，绕过 ORM 的脚本会产生不同状态。
- seed 脚本直接 SQL 写入 demo paid orders/payment/invoice，使数据库看起来有收入，但未标记独立 environment/source。
- 没有 CI 自动比较 metadata 与 head schema，也没有“从零建库 + 旧版本升级”双路径测试。

退出条件：建立 forward-only 修复迁移；禁止重写已发布 migration；在临时 PostgreSQL 中执行 `upgrade base→head`、ORM CRUD smoke 和 schema diff。

## 租户与所有权

- `TenantOwnedMixin` 为多数对象增加非空 tenant FK，是可复用基础。
- Policy 则允许 null 表示 global。这是可行模式，但 API、schema 和 workflow 没有统一解释。
- `PolicyOut.tenant_id` 仍定义为非空 UUID，和数据库相冲突。
- PolicyRule 是 tenant-owned，却可引用全局 Policy；当前 create API 又只允许 own tenant Policy。
- Deliverable 的 user_id/company_id 没有 FK；AgentRun user_id/task_id、AnalyticsEvent user_id、Entitlement user_id/resource_id 也缺引用完整性。
- platform-owned 数据与 tenant-owned 数据没有显式 owner_type/visibility。

建议使用：`policy_sources → policy_documents → policy_versions → policy_chunks`，其中 source/document/platform-owned，tenant overlay 通过 visibility/tenant_id 管理。不要让业务语义只依赖 nullable FK。

## 约束与完整性缺口

| 优先级 | 缺口 | 风险 | 建议约束 |
|---|---|---|---|
| P1 | Company credit code 无 tenant unique | 重复画像和错误匹配 | unique(tenant_id, normalized_credit_code) |
| P1 | Opportunity 无去重/版本键 | 每次报告重复插入 | unique(company_profile_version, policy_version, engine_version) |
| P1 | Payment provider event 无唯一账本 | webhook replay/重复权益 | unique(provider, event_id/trade_no) |
| P1 | Entitlement 无业务唯一约束 | 重复授权 | unique(order_id, product_id, resource_type, resource_id) |
| P1 | 状态自由字符串 | 非法转换和分析污染 | enum/check + transition service |
| P1 | 金额用 float type annotation | 序列化/计算精度混乱 | API Decimal/string minor units；DB Numeric |
| P1 | JSON 无 schema/version | 无法升级和治理 | JSON schema name/version + typed tables for core facts |
| P2 | 时间字段混用 default/server_default | 不同写路径不一致 | DB UTC server default + explicit update policy |
| P2 | 缺 tenant-aware composite FK | 对象 ID 可与错误 tenant 组合 | composite ownership validation/RLS |

## 企业画像目标模型

当前 Company 基础字段 + `metadata_json` 无法支持证据和冲突。建议：

```text
Company
CompanyProfileVersion (immutable snapshot, status, completeness)
CompanyFact
  - fact_type / typed_value / unit / effective_at
  - source_document_id / source_span_id
  - confidence / extraction_method / verified_by
CompanyDocument
DocumentVersion → ParseRun → DocumentChunk/Span
FactConflict / UserConfirmation
```

生成任何 decision 时固定引用 profile version；新资料不会静默改写旧报告。

## 政策与证据目标模型

```text
PolicySource (authority, canonical URL, collector, trust tier)
PolicyDocument (canonical identity)
PolicyVersion (content hash, valid_from/to, published/effective/deadline)
PolicyAttachment
PolicyChunk / PolicySpan (page, section, offsets, embedding)
EligibilityCriterion (typed DSL, blocking, version)
DecisionSnapshot
CriterionResult
EvidenceLink (policy span + company fact/span)
```

Policy 变更产生新版本和增量重评，不覆盖旧 content。source URL、抓取时间和 hash 共同支持 provenance。

## 工作流目标模型

Task 只表示业务意图，还需要：

- WorkflowDefinitionVersion；
- WorkflowRun / StepRun / Attempt；
- lease owner/expiry、idempotency key、retry policy；
- ApprovalRequest/Decision；
- Artifact/DeliverableVersion；
- Event/Outbox；
- CostUsage（provider/model/tokens/OCR/storage/human minutes）；
- Error classification 和 recovery action。

RevisionRequest 必须验证 deliverable 属于同一 task/tenant；修订应创建新 DeliverableVersion，不原地覆盖。

## 商业数据目标模型

```text
Product → PriceVersion
CustomerAccount / BillingProfile
Order → OrderLine
PaymentAttempt
ProviderEvent (immutable/idempotent)
LedgerEntry
EntitlementGrant / Revocation
Subscription / UsageMeter (后续)
Refund / Dispute
InvoiceRequest / TaxInvoiceReference
ReconciliationRun / Difference
```

“paid”应是账本事件聚合结果，不允许由普通业务路由直接赋值。正规税务发票只保存税务平台返回的号码/文件/状态；内部 PDF 需使用不同实体和文案。

## Analytics 与数据治理

- 分析事件必须有 event catalog、owner、version、PII classification、retention 和 server/client trust level。
- 收入、付款、任务成功、交付验收必须由服务端/账本产生；客户端不得自报。
- AuditLog 应 append-only、限制更新/删除、包含 actor、tenant、action、target、result、request/trace、reason 和安全字段；敏感正文不直接存。
- 定义数据删除图：primary DB、OSS、search/vector、logs、analytics、backups、provider retention。
- 为 schema migration、backfill、删除和恢复建立 runbook 与审计记录。

## 优先级

### P0

- 修复 migration drift；冻结商业和任务新功能直到 schema Gate 生效。
- 修正 global/private policy ownership 和跨租户 scope。

### P1

- Profile/Policy/Decision immutable version + evidence links。
- 商业账本、provider event、outbox/idempotency。
- 关键 FK/unique/check/RLS 和状态机。
- 分析/审计 schema 与 retention。

### P2

- 使用计量、订阅、数据导出/删除、政策变更重评和成本归因。

### P3

- warehouse/semantic layer、跨 vertical schema registry 和高级数据产品。
