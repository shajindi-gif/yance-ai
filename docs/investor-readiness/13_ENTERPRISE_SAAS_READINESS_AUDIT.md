# Enterprise SaaS、商业化与融资演示专项审计

审计范围：用户要求第 11–40 节，包括前端信息架构、Homepage、Workspace、Opportunity、Application、Agent Operations、Admin、Analytics、Billing、Enterprise Readiness、安全、可观测性、性能、真实数据、投资人指标、Demo、Data Room、测试、CI、数据库、代码质量、LLM Provider、成本和 Feature Flag。

## 结论

现状是“营销页面较多、后端对象已有雏形的可点击 MVP”，不是成熟 Enterprise AI SaaS。真正的缺口集中在四条链：

1. 登录后仍是一个报告生成 Dashboard，没有持久 Workspace 与 Application 工作台；
2. 数据对象存在不等于业务闭环，Admin、Agent Trace、Eval、Billing、Usage 都没有可运营界面；
3. 真实性边界不足，Demo payment、Mock Agent、静态政策样例与正式页面混用；
4. 根级 CI、E2E、迁移验证、依赖安全和可恢复部署未形成 release gate。

因此前端改版不能先于 Phase 1 安全止血，也不能用新 UI 掩盖不存在的 backend。设计系统与主流程将在兼容当前 Next.js/FastAPI/PostgreSQL 的前提下渐进落地。

## 11–17：前端产品面审计

### 视觉与设计系统

| 项目 | 当前事实 | 评级 | 目标状态 |
|---|---|---:|---|
| Design system | 单一 `globals.css` 约 5,357 行；大量 inline style；无 token/component package | P1 | token、typography、spacing、semantic color、组件状态、可访问性规则 |
| App shell | 根 layout 对所有页面渲染营销 Header/Footer/SmartAgent | P1 | `(marketing)`、`(auth)`、`(app)`、`(platform-admin)` 分离布局 |
| Auth guard | localStorage bearer + client effect redirect | P1 | 同源 HttpOnly session、server/middleware guard、tenant context |
| Loading/error | 页面各自实现；无统一 `loading.tsx`、`error.tsx`、`global-error.tsx` | P1 | skeleton、retry、timeout、empty/error boundary 契约 |
| 图片/字体 | 原生 `img`；Google Fonts 外链 | P2 | `next/image`、自托管字体、LCP/CLS 预算 |
| Docker | Dockerfile 复制 standalone，但 Next config 未生成 standalone | P1 | 构建产物与镜像契约一致并有 smoke test |

参考 Harvey、Hebbia、Glean、Sierra、Decagon、Linear、Vercel 只用于提取“可信、高密度、克制、一致”的原则，不复制布局、素材或品牌表达。禁止为了“AI 感”堆叠渐变、玻璃拟态、机器人和未经证实的社会证明。

### Homepage

当前首页内容丰富但价值主线发散，包含产业研究、政策、园区、路演等多个方向，5 秒内不容易形成单一 Job-to-be-Done。改版验收必须能直接回答：

- Yance 是企业政策机会发现与申报执行平台；
- 面向企业、园区和专业服务机构；
- 完成画像、扫描、资格、证据、缺口、材料和任务；
- 区别于通用聊天工具的是结构化企业上下文、政策知识、确定性规则、证据、持久工作区和执行历史；
- 主行动是 `Start Policy Scan`，次行动是进入明确标注 Demo 的演示。

`Trusted / Usage Evidence` 只能来自可追溯数据库或签署授权的客户材料。没有证据时显示产品能力、方法论或空状态，不放 Logo、收入、用户数、准确率和评价。

### App Dashboard 与 Golden Journey

当前 `/dashboard` 把企业创建、模型选择、报告、订单、演示支付和统计放在一个客户端页面，并默认选择第一个企业。下列目标路由均不存在或不完整：

- `/opportunities` 与详情的 Eligibility/Evidence/Requirements/Documents/Timeline/Source；
- `/companies` 与版本化 Company Profile、资料来源和完整度；
- `/applications/[id]` 企业级工作台；
- `/agents` Agent Operations；
- `/documents`、`/knowledge`、`/settings`、`/billing`；
- `/admin/*` 平台后台。

应用主导航和 Home Dashboard 必须由真实查询驱动。Opportunity Score、Potential Funding、Documents Missing、Recent Agent Runs、Next Best Actions 等指标需要服务端定义、更新时间、空状态和 drill-down；禁止前端推测。

### Application Workspace

现有 `Application` 仅保存 `status` 和自由 JSON，Task/Deliverable 也不足以支持 Overview、Requirements、Documents、Generated、Tasks、Evidence、Activity。目标需要先补数据模型和 API，再实现 UI：

- ApplicationVersion / Requirement / MaterialStatus；
- Task assignee、due date、dependency、status history；
- Artifact/ArtifactVersion、approval、comment、revision；
- Evidence/SourceSpan 双向引用；
- Activity actor、timestamp、reason；
- Agent Panel 的 Ask/Generate/Check/Fix/Explain 均映射到真实 workflow command，并显示 run 状态。

任何按钮在后端 command、权限、idempotency 和错误状态完成前不能上线。

### Agent Operations

当前没有 Agent catalog 或 `/agents`。AgentRun 只有摘要字段，无法可信计算 success rate、latency 和 tasks completed。必须先实现 `12_AGENT_ARCHITECTURE_RAG_EVAL_SPEC.md` 的 Harness；随后列表指标全部从 AgentRun/Step/ToolCall/Evaluation 聚合，分母包括失败和取消，不能只统计成功样本。

## 18：Admin Dashboard

当前没有 platform admin 身份模型或管理 UI，tenant owner 也不能等同平台管理员。目标信息架构：

```text
/admin
  /users
  /organizations
  /companies
  /agent-runs
  /workflow-runs
  /llm-usage
  /costs
  /documents
  /policies
  /evals
  /errors
  /billing
  /feedback
  /system-health
  /investor-metrics
```

跨租户访问要求独立 platform role、MFA、reason-required、不可变 AuditLog 和敏感字段遮罩。Support impersonation 若后续引入，必须显式 banner、时间限制和审计，不能复用普通 tenant JWT。

## 19：Analytics

已有 `AnalyticsEvent` 表和一个写入 API，但没有 canonical event registry、schema version、deduplication、session/source、consent、retention、测试和漏斗。现有 demo stats 不是投资人指标系统。

第一版事件注册表必须覆盖：

```text
signup_completed
company_created
company_profile_completed
document_uploaded
policy_scan_started
policy_scan_completed
opportunity_opened
application_created
report_generated
document_generated
checkout_started
payment_completed
```

每个事件定义 actor、tenant、entity IDs、occurred_at、schema_version、idempotency_key 和允许 properties。`payment_completed` 只能由验证后的支付领域事件产生，不能由浏览器或 demo-pay 伪造。

## 20：商业化

当前 Product/Order/Payment/Invoice/Entitlement 是骨架，存在客户端金额、demo-pay 直接 paid、真实 webhook 不原子发权益、发票对象写错、银行接口字段错误等 P0。不能在此基础上直接包装 Free/Pro/Business/Enterprise。

目标模型：Plan → PriceVersion → Subscription → SubscriptionItem/Entitlement → UsageMeter → UsageRecord → Invoice。各层的 Policy scans、Companies、Reports、Documents、Agent runs、Users、Storage 必须服务端计量；超额处理、宽限、退款、取消、降级和历史价格都要有状态机。

Phase 1 先恢复交易完整性；Phase 9 才正式交付订阅和企业商业化。此前所有支付页面必须明确 sandbox/demo 或关闭。

## 21：Enterprise Readiness

| 能力 | 当前 | 缺口 | 优先级 |
|---|---|---|---:|
| Organization/Workspace | `Tenant` 近似组织 | 无 membership/workspace 边界和切换 | P1 |
| RBAC | owner/admin/member/viewer 已有 | role scope、邀请、测试矩阵不足 | P1 |
| Audit Log | 表存在 | 核心写操作未统一写入、无检索/保留/完整性 | P1 |
| Data Isolation | 手写 tenant filter | 无 scoped repository、RLS、自动化矩阵 | P0 |
| API Keys | 无 | hash、scope、expiry、rotate、revoke、last-used | P2 |
| Usage/Billing | entitlement 骨架 | 计量、quota、订阅、账单不完整 | P1 |
| Export/Delete | 无完整流程 | async export、审批、备份删除传播 | P1 |
| Data Retention | 仅文案 | policy、legal hold、自动执行和证据 | P1 |

## 22–24：安全、可观测性与性能

安全主清单和 P0 见 `06_SECURITY_AUDIT.md`。新增确认项：

- 根级 `.env.example` 与后端 example 当前没有被 Git 跟踪，环境契约不可复现；
- 根级 `SECURITY.md` 不存在；
- 公司财务标识被写成代码默认配置；
- 前端生产依赖审计有 3 个 High；
- JWT 在 localStorage，登录/LLM/上传缺少共享 rate limit；
- PDF/HTML 渲染存在注入与 SSRF/LFI 风险；
- demo payment、跨租户路由和全局/私有 Policy scope 是上线阻断项。

Observability 当前只有 request_id 和结构化请求日志雏形。目标日志 context 必须有 `request_id`，Agent/Workflow 场景增加 `run_id`、`tenant_id`；字段 allowlist 和 redaction 禁止企业正文、Prompt、token、密码、支付凭证进入日志。API latency、queue、LLM/model cost、tool、evaluation、billing 必须可串到同一 trace。

性能不能只看首页 Lighthouse。预算至少覆盖：首页 LCP/CLS/INP、Dashboard 首屏查询、Policy Search P95、Agent Workspace streaming/轮询、分页与大文档。当前 build 首页 104 kB、Dashboard 106 kB first-load JS 可作为基线，但没有真实网络、设备和 API 数据，不能声明 Core Web Vitals 达标。

## 25：真实数据原则

当前存在以下污染边界：SmartAgent mock response 在匿名/API 失败时给确定性政策回答；demo-pay 写正式 paid/order/entitlement；seed demo 脚本写 paid/payment/invoice；部分静态页面用 Sample output，但标识不统一。

强制控制：

1. Demo tenant、Demo actor、Demo records 均有不可移除的 `is_demo`/dataset namespace；
2. Demo revenue、payments、usage 永不进入正式融资指标；
3. API 错误不能 fallback 成看似真实的回答；
4. UI 对 Demo/Example/Sample 使用统一 badge；
5. 没有事实就展示 empty state；
6. metrics query 默认 `is_demo = false` 并有回归测试。

## 26–27：Investor Metrics 与 Demo Mode

`/admin/investor-metrics` 当前不存在。目标指标必须有定义、时间窗口、timezone、排除 demo 规则和 drill-down：

- Users/Active Users/Organizations/Companies；
- Policy Scans/Applications/Reports/Agent Runs；
- Successful/Failed Runs/Documents Generated；
- PoC Accounts/Paying Customers/Revenue；
- LLM Cost/Cost per Run；
- signup → profile → scan → opportunity → application → deliverable → paid funnel。

其中 PoC Account 需要显式 lifecycle，Revenue 必须来自经校验的支付/会计口径，不能由 `orders.status=paid` 简单相加。

当前 `/demo` 只是重定向注册，没有 3–5 分钟演示链。Phase 10 将建立 3–5 个明确标注 DEMO 的隔离案例，使用固定版本资料和政策快照，预生成或稳定运行真实 Harness。演示失败时应展示可解释错误，不以 mock answer 冒充成功。

## 28：Data Room

当前有零散技术与运维文档，但 `/docs/data-room/` 指定材料尚未建立。Phase 10 才生成正式材料，且每份文档必须引用真实实现、migration、测试或运行证据；未来态单独标记 Roadmap。禁止把架构图中的计划组件写成已部署。

## 29–30：Testing 与 CI

Phase 0 实测：

| 检查 | 结果 | 解释 |
|---|---|---|
| Frontend production build | PASS | 25 routes 编译/类型/静态生成通过；Google Fonts 优化警告 |
| Frontend tests/E2E | NOT PRESENT | package scripts 和测试文件均不存在 |
| Frontend dependency audit | FAIL | 3 High：Next.js、PostCSS、nanoid |
| Backend pytest | PASS, insufficient | 5 tests；总覆盖率 45%，核心 policy/payment/task 低覆盖 |
| Backend Ruff | FAIL | 290 errors |
| Eval runner | MISLEADING PASS | 2 cases 只校验结构，不运行模型质量 |
| Benchmark | FAIL | 硬编码 `/Users/.../env.prod` 路径 |
| Migration graph | PARTIAL | 单一 head；无可用 PostgreSQL/Docker daemon，未跑 base→head |

CI 文件位于 `yance-ai/.github/workflows`，GitHub 不会把嵌套目录当仓库级 workflow。根级 CI 当前等同不存在，也没有前端 job、security scan、migration schema diff、E2E 和 branch required check 证据。

核心 E2E 必须覆盖 Register → Create Company → Upload → Scan → Opportunity → Application → Generate → Download，并增加跨租户、未支付、无证据、worker retry 和 human reject 的负向路径。

## 31–35：数据、代码、LLM、成本与 Feature Flag

### 数据库

现有实体可渐进复用：Tenant、User、Company、Document、Policy、PolicyRule、Opportunity、Application、Task、Deliverable、AgentRun、AnalyticsEvent、AuditLog、Product、Entitlement、Order、Payment、Invoice。缺失项不能通过一次破坏式迁移补齐。

实施原则：additive table/column → 双写/回填 → read switch → 观察 → 后续清理。每个 migration 需要 base→head、现网升级副本、downgrade policy、锁表/耗时说明和 ORM diff。已确认 Task/Deliverable migration 与 ORM 存在 drift，先修复后扩展。

### 代码质量

当前存在 `models.py.bak`、290 个 Ruff 问题、页面内重复 fetch、`any`、单体 CSS、硬编码 provider/价格/状态/路径。清理按“有测试保护且与当前 Phase 相关”执行，不做一次性全仓机械重写。

### LLM Provider

已有 `LLMProvider.complete()` 和 Qwen/DeepSeek/OpenAI-compatible/Anthropic provider 雏形，但目标 `chat`、`structured_output`、`embedding` 未统一；业务仍可直接选择 provider，模型策略、fallback、成本和 schema repair 没有统一 Gateway。Phase 4/5 将兼容现有接口增加 ModelProfile：primary、fallback、cheap、embedding，并将业务代码禁止直接实例化 provider。

### 成本与预算

AgentRun 目前不完整记录 input/output tokens、标准化价格版本和 cost。目标账本按 provider/model/price_version 计算，预算支持 user、organization、workflow；preflight reservation + final settlement 防止并发超额。未知价格不能记 0，应标记 `cost_unknown`。

### Feature Flag

当前无 Feature Flag。第一版只需 database-backed flag + environment default + tenant/user targeting + audit，不引入重型平台。`beta feature`、`new agent`、`new workflow`、`experimental UI` 默认关闭；安全/计费权限不能仅依赖前端 flag。

## 优先级汇总

### P0

- 关闭 demo payment/paid task、修支付权益和跨租户边界；
- 修 migration drift、PDF/HTML 注入、资格硬门槛误判；
- 移除代码中的财务配置默认值并完成轮换/历史扫描；
- 修正无法证明的安全、客户、收入、准确率和产品声明。

### P1

- 安全 session、root CI、E2E、持久 workflow、Harness trace；
- Organization/Membership、Workspace、Application、Evidence、Artifact；
- Admin、Analytics registry、Usage/Cost、真实 Eval；
- Next.js High 漏洞和 Docker standalone 契约。

### P2

- Enterprise API Keys、完整 retention/export/delete、Feature Flag；
- Design system、性能预算、Agent Operations、投资人 metrics；
- 订阅套餐、invoice、企业计费、Demo/Data Room。

### P3

- SSO/SCIM、高级实验平台、多区域、跨 vertical SDK；仅在客户需求和首个闭环留存成立后推进。

## “为什么不是 ChatGPT”验收

每项新功能必须至少强化一项不可由单次聊天替代的资产：版本化企业事实、政策结构化规则、原文证据、确定性资格 Gate、持久申报 Workspace、审批与执行历史、可重复 Eval、组织级权限与数据隔离、真实使用/成本数据。若一项工作只增加聊天入口、营销文案或视觉效果，而不增强上述资产，则不得进入主路线。
