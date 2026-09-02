# 后端审计

## 总评

FastAPI 后端提供了较完整的领域名词和 API 骨架，但关键路径的事务、授权和状态完整性不足。当前最危险的模式是：用一个字符串状态代表已经发生的现实事件，例如付款、发票、任务完成和质量通过，却没有不可伪造的事件来源和一致性约束。

## 组件概览

| 层 | 实现 | 评价 |
|---|---|---|
| API | 13 个 route modules，统一 `/api/v1` | 可读，但路由承担过多业务逻辑 |
| Domain | SQLAlchemy models + Pydantic schemas | 有领域骨架，缺状态机、约束和 repository/service 边界 |
| Persistence | PostgreSQL + Alembic + pgvector | 适合产品，但 migration/ORM 已漂移 |
| External | OSS、Qwen/DeepSeek/OpenAI/Claude、支付宝/Stripe | 多为直接 SDK/HTTP 调用，缺可靠性和治理层 |
| Async | FastAPI BackgroundTasks | 不满足长任务、重试和进程恢复需求 |
| Logging | structlog request middleware | 仅请求日志，无完整业务与安全审计 |

## P0 缺陷

### 1. 商业状态可伪造

- `/payments/demo-pay` 对 owner/admin/member 开放，直接创建 paid Order、completed Payment、active Entitlement 和 generated Invoice。
- `/tasks/{task_id}/pay` 不调用支付供应商，直接把任务和订单设为 paid。
- 两个路由都被生产 router 无条件加载，前端还主动调用。

这不是“支付尚未接完”的普通 TODO，而是可被外部用户调用的收入和授权绕过。

### 2. 订单定价和回调不可信

- `OrderCreate` 接受客户端 `product_code` 和 `amount`，`create_order` 原样写入；攻击者可自定价。
- 支付宝回调仅验签，未核验 `app_id`、seller、`total_amount`、币种和本地订单期望值。
- Stripe/支付宝回调只改 Payment/Order，不原子创建 Entitlement。
- 没有 provider event 唯一键、幂等表、退款/冲正、对账任务和 ledger。

### 3. 银行转账和发票路径确定性失败

- 银行转账代码引用不存在的 `Order.user_id`、`Principal.user_id`、`Payment.method`、`Order.total_amount`，且未导入 `datetime/timezone`。
- 银行核销只要求普通已登录用户，没有平台财务角色，也没有 tenant scope。
- 发票创建构造 `invoice` 后却执行 `db.add(order)`，随后 refresh 未持久化对象。
- Decimal 被直接放入 JSON item 的风险未处理；发票模板输入未转义。

### 4. Task/Deliverable schema drift

模型中的 `Task.progress/current_stage` 不存在于迁移 0008；迁移的 `tasks.metadata` 不存在于模型。Deliverable 继承 `TimestampMixin`，但迁移没有 `created_at/updated_at`；迁移的 `metadata` 模型也没有。任务查询和 worker 在标准迁移后的数据库上会报列不存在。

### 5. 授权边界

- `/tasks/admin/all` 位于 `/{task_id}` 之后，静态路径可能被 UUID 路由遮蔽；若修正顺序，它又允许任意租户 Owner 查询所有租户任务。
- policy evaluator 仅按 Policy ID 查询；全局政策可以访问，但其他租户的 private policy 也可访问。
- 平台 Admin 与租户 Owner 被混为一谈。

## API 与领域设计问题

| 优先级 | 问题 | 影响 |
|---|---|---|
| P1 | 没有统一 idempotency key | 重试可能重复创建订单、支付、机会、任务 |
| P1 | 状态全为自由字符串 | 可写入非法转换，无法在 DB 层保证状态机 |
| P1 | 事务边界碎片化 | demo pay 分多次 commit；中途失败留下部分状态 |
| P1 | API 错误模型不统一 | 前端只能依赖 `detail` 字符串，无法可靠处理 |
| P1 | UUID 字符串手工转换 | `policy_engine` 无效 UUID 可变成 500，而非标准 422/400 |
| P1 | route 内同步数据库 + 外部 LLM | worker 阻塞、连接占用、超时难治理 |
| P1 | 无 pagination/limits | list companies/documents/orders/opportunities 可无限增长 |
| P1 | 分析与 AgentRun 可由客户端写 | 不能作为可信审计或计费数据 |
| P2 | sync Session 与 async route 混用 | 并发能力、取消和连接管理难预测 |
| P2 | response model 覆盖不完整 | 多个 dict response 无契约和版本保证 |

## 认证与租户

已有优点：Argon2 推荐密码哈希；JWT 有 exp；从数据库重新读取当前角色而不是信任 token 中旧角色；多数业务查询有 tenant filter；OSS key 包含 tenant UUID。

缺口：

- login 无 rate limit、失败计数、锁定、MFA、验证码或异常检测；注册限流只在单进程内存中，四 worker 各自独立且重启清空。
- 无 refresh token、session 列表、撤销、密码重置/变更、邮箱验证、邀请和服务账号/API key。
- `get_principal` 验证 User active，但不验证 Tenant active。
- JWT 没有 issuer/audience/jti/session id；密钥轮换和泄露响应无实现。
- 数据库无 RLS；应用层每个查询手写 scope。
- User email 数据模型是 tenant 内唯一，但 public register 又执行全局 email 检查；产品规则不一致。

## 文档上传

当前上传流程只做到：安全化文件名、生成租户前缀 object key、预签名 PUT、检查对象存在、把客户端提交的 checksum 保存。

缺少：

- server-side size、MIME、magic bytes、扩展名 allowlist；
- SHA-256 实际校验、恶意软件扫描、压缩炸弹保护；
- OCR/解析沙箱、失败隔离、超时和资源限制；
- 文档状态机、删除/保留、legal hold、访问下载 URL；
- parser/chunker/indexer 和与画像字段/政策证据的关联。

## 任务执行

`BackgroundTasks` 在返回 HTTP 后仍由同一 Web 进程执行。部署有 4 个 Uvicorn worker，但没有共享队列、worker 心跳、lease、重试或 shutdown drain。进程退出会丢失 queued/running 任务；重复 execute 存在竞争条件。

所有 task type 最终都运行同一 `match_policies_for_company` 和 PDF 生成器。`application_draft` 并未生成申报初稿。生成的 `pdf_bytes` 在 worker 中被丢弃，下载时重新计算。quality_score 固定为 88，profile_reader latency 固定 50 ms。RevisionRequest 只写 pending，没有处理流程。

## Logging、Analytics 与 Audit

- request middleware 有 request_id、path、status、duration，是好的最小起点。
- 没有 user/tenant 安全绑定、trace/span、model call、retrieval、DB、queue、payment correlation。
- `AuditLog` 模型存在，但代码没有写入点；公开“所有写操作审计”不成立。
- `AnalyticsEvent` 由客户端任意提交，缺事件 allowlist、schema、PII 筛查和可信 server events。
- 无 Prometheus/OpenTelemetry/Sentry 等实现，无告警或 SLO burn rate。

## 建议后端分层

```text
app/
  api/                  # HTTP validation/auth only
  domains/
    identity/
    profiles/
    policies/
    cases/
    agents/
    commerce/
  repositories/        # tenant-scoped access
  workflows/           # durable orchestration
  integrations/        # model/payment/OSS/OCR adapters
  platform/             # outbox, audit, idempotency, observability
```

每个 command 应使用单事务完成状态变更 + outbox event；外部调用由 worker 消费，provider event 先持久化再处理。不要在路由中多次 commit。

## 修复优先级

### P0

1. 删除/环境封锁 demo pay 和 task pay；
2. 新增 schema 对齐迁移并做从零/升级测试；
3. 修复商业账本、金额真源、回调校验和权益原子发放；
4. 引入 platform admin，修正静态路由和所有跨租户查询；
5. 安全化 PDF/发票生成和 worker 隔离；
6. 资格结论强制 human review。

### P1

- 统一 tenant repository + RLS、idempotency/outbox、durable queue、API error/version/pagination。
- 完成 auth 生命周期、AuditLog、上传安全和 observability。
- 用 OpenAPI 生成前端 client 并加入 contract test。

### P2/P3

- usage metering、webhook/API keys、企业 SSO/SCIM、细粒度 ABAC。
- 根据负载拆分 ingestion/agent rendering worker；不要提前拆核心事务域。
