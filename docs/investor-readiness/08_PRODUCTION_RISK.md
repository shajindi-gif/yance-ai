# 生产风险登记册

## 使用方式

本文件是本轮审计的统一风险登记册。优先级定义：

- **P0**：阻止生产上线、可能造成严重安全/财务/合规后果；
- **P1**：显著阻碍企业成交、融资或可靠运营；
- **P2**：重要产品与规模化升级；
- **P3**：可优化项。

状态均为 `OPEN`，除非后续有代码、测试和运行证据满足退出条件。仅修改文案或隐藏按钮不能关闭底层风险。

## P0

| ID | 风险 | 概率/影响 | Owner | 退出证据 |
|---|---|---|---|---|
| P0-01 | demo pay 与 task pay 可直接置 paid/授予权益 | 高/严重财务 | Backend + Security | production 不注册路由；负向 API 测试；sandbox 真实支付闭环 |
| P0-02 | 订单、银行转账、发票路径存在定价伪造、越权和运行时错误 | 高/严重财务 | Backend + Finance | 服务端 PriceVersion；platform finance RBAC；银行/发票集成测试 |
| P0-03 | Task/Deliverable ORM 与 migration 漂移 | 高/生产不可用 | Data/Backend | base→head、upgrade、schema diff、CRUD smoke 全通过 |
| P0-04 | platform admin/tenant owner 混淆和潜在跨租户读取 | 中高/严重数据泄露 | Security + Backend | 统一 scope + RLS；全资源跨租户矩阵 100% |
| P0-05 | WeasyPrint HTML 未转义，存在注入、SSRF/LFI 和 DoS 面 | 中/严重数据与主机风险 | Security + Backend | escape/URL fetcher deny/sandbox；恶意 payload 测试 |
| P0-06 | 资格 Gate 把安全事故/环保/信用条件软化并可能输出 ELIGIBLE | 高/严重业务与声誉 | AI + Domain | DSL/回归集；严重 FP 达 Gate；强制人审 |
| P0-07 | 安全、隐私、备份、模型和产品公开声明无证据或被代码反证 | 高/法律和成交 | CEO/Legal/Security | claim-control register；法务签核；页面与实际一致 |
| P0-08 | 支付 webhook 未校验完整商业字段且不原子发放权益 | 中高/财务与客户交付 | Backend + Finance | immutable provider event、幂等、金额/商户验证、对账、权益测试 |

## P1

| ID | 风险 | 影响 | 退出证据 |
|---|---|---|---|
| P1-01 | global policy 与 tenant policy API 语义冲突 | 检索/CRUD/序列化失败和数据越权 | ADR + visibility 模型 + contract/tenant tests |
| P1-02 | 文档上传无校验、扫描、解析、OCR、chunk/index | 核心“导入资料”价值不成立，上传攻击面 | quarantine ingestion pipeline + security tests |
| P1-03 | 任务依赖 Web BackgroundTasks，无恢复/锁/重试 | 重启丢任务、重复执行和成本 | durable queue、lease、idempotency、recovery test |
| P1-04 | 三种 task type 实际运行同一报告管线 | 申报草稿/诊断属于功能性误导 | 每类 versioned workflow + acceptance test |
| P1-05 | RAG 无 source/version/chunk/citation/ACL | 结论不可证、不可复现 | source-to-citation data model + retrieval eval |
| P1-06 | Eval CI 不执行引擎，benchmark 仅 16 例且准确率 43.8% | AI 质量不可控 | 冻结分桶集、真实 runner、release thresholds |
| P1-07 | 登录/会话无限流、MFA、重置、撤销和 tenant active | 账号接管与企业安全问卷失败 | account lifecycle + security regression |
| P1-08 | JWT localStorage 且无 CSP | XSS 可窃取会话 | HttpOnly session/BFF + CSP tests |
| P1-09 | AuditLog 未写入；无可验证 180 天审计 | 争议、安全事件和企业成交风险 | append-only audit coverage test + retention proof |
| P1-10 | 无 metrics/traces/error aggregation/SLO/alert | 故障不可发现、AI 成本不可解释 | OTel/metrics/error backend + dashboard/alerts/runbook |
| P1-11 | 生产是 Mac/Docker Desktop/Cloudflare Tunnel 单点 | 无 SLA，重启/睡眠即中断 | managed compute/DB/object store、HA/backup/restore |
| P1-12 | CI 位于嵌套 `.github`，前端没有 CI/tests | 质量 Gate 实际不运行 | 根级 required checks，backend/frontend/e2e/migration build |
| P1-13 | 前端 Docker standalone 配置不成立 | 标准发布失败 | next standalone 配置或修订 Dockerfile + image smoke |
| P1-14 | API contract 漂移，尤其 Alipay/Report/Policy | 客户路径运行时失败 | generated client + OpenAPI contract tests |
| P1-15 | 机会重复 insert、无 profile/policy/engine version | 数据膨胀、历史不可复现 | immutable decision key + idempotent upsert |
| P1-16 | LLM 无 retry/budget/quota/redaction/injection guard | 成本、可靠性、数据外泄 | Model Gateway policy + adversarial tests |
| P1-17 | 产品价格、条款、SKU、任务价格不一致 | 客诉、合同和收入分析错误 | 服务端 PriceVersion + legal/product sync |
| P1-18 | 无平台 Admin、内容发布、失败任务和对账控制面 | 无法规模化服务客户 | platform admin MVP + audited operations |
| P1-19 | SmartAgent 和政策页使用硬编码/静默 fallback | 过时或错误政策被当事实 | source/time label + no silent factual mock |
| P1-20 | 无 IaC、staging、回滚、迁移锁、备份自动化 | 发布和恢复不可重复 | IaC + staged release + restore drill evidence |
| P1-21 | 上传/LLM/支付/OSS 供应商数据流和 DPA 未证明 | PIPL/跨境/合同风险 | data flow, subprocessor register, DPA, retention policy |
| P1-22 | 业务 JSON 无 schema/version/大小限制 | 数据漂移、prompt/log 污染 | schema registry/typed facts/input limits |
| P1-23 | 无统一 Agent Harness、Step/Tool/Verifier/Retry 轨迹 | Agent 名称存在但关键任务不可恢复、不可验证、不可审计 | Harness 数据模型、状态机、durable execution、trace Admin |
| P1-24 | PolicyRule 自由 JSON，缺 Policy/Rule/Material/Benefit/Deadline 结构层 | Eligibility 仍依赖 LLM 猜测，政策更新不可控 | 版本化关系层、typed rule DSL、source spans、发布审批 |
| P1-25 | Eval runner 不执行系统且无真实 Eval Dashboard | 质量指标不可作为发布或融资证据 | 五类真实 runner、EvalRun 模型、无数据空状态、CI Gate |

## P2

| ID | 风险/机会 | 建议 |
|---|---|---|
| P2-01 | 营销与应用共用 layout | route groups + 独立 app shell |
| P2-02 | 无企业级 case workspace | 任务、材料、负责人、截止日、评论、审批、活动流 |
| P2-03 | 无 portfolio/多企业批量视图 | 园区/专业机构版本 |
| P2-04 | 无 SSO/SCIM/API key/webhook/usage quota | 企业与平台集成层 |
| P2-05 | Analytics 只有事件表，无指标治理/归因/实验 | server event catalog + funnel + retention/cohort |
| P2-06 | 单一 whole-document vector retrieval | hybrid search、metadata filter、rerank |
| P2-07 | 无通知和政策变化增量重评 | scheduler + notification preferences |
| P2-08 | 前端全局 CSS、inline style、`any` 较多 | design system、feature modules、typed API |
| P2-09 | 无订阅、用量、合同和毛利成本归因 | billing/metering/cost ledger |
| P2-10 | 无数据主体导出/删除/注销产品流程 | privacy operations + deletion graph |
| P2-11 | 模型与 prompt/template 版本缺控制面 | registry、approval、rollout、rollback |
| P2-12 | 部署文档三套架构互相冲突 | 单一 current-state + target-state + ADR |

## P3

| ID | 项目 | 建议 |
|---|---|---|
| P3-01 | 跟踪的 `models.py.bak` 以及工作区中的 `__pycache__/.DS_Store` 噪音 | 删除死文件并强化 `.gitignore`/清理脚本 |
| P3-02 | 文档含个人绝对路径和过时说明 | 参数化 runbook、owner/review date |
| P3-03 | 代码格式、长函数和重复 API 调用 | lint/formatter、service extraction |
| P3-04 | SEO/accessibility/i18n 基线不足 | sitemap/robots/schema、axe、语言策略 |
| P3-05 | Chrome/桌面/移动端路线过早 | 主 Web 工作流稳定后按真实需求验证 |

## Top 10 风险的 30 天处置顺序

1. 封锁 P0-01；
2. 修 P0-03 并建立 migration CI；
3. 修 P0-02/P0-08 商业账本；
4. 修 P0-04 tenant/platform auth；
5. 修 P0-05 PDF renderer；
6. 冻结自动资格，修 P0-06；
7. 完成 P0-07 claim reconciliation；
8. 根级 CI + contract/e2e；
9. durable workflow；
10. ingestion + evidence model。

## 风险接受规则

- P0 不允许风险接受后直接生产上线。
- P1 如暂缓，必须有明确 Owner、截止日、补偿控制和客户披露。
- 所有关闭项必须同时具备：代码/配置、自动化测试、staging 运行证据、文档/Owner；仅“已人工测过”不足以关闭。
