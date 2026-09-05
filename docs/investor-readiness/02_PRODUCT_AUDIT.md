# 产品审计

## 产品判断

产品方向正确：政策机会发现与申报执行是高信息密度、强证据、跨角色、长周期的垂直工作流，适合 Agent + Knowledge + Workflow。当前实现的问题是价值主张已经到“完成工作”，产品本体仍主要停留在“生成一次报告”。

投资人会看到领域理解和产品野心，但也会立即追问：数据从哪里来、为什么可信、谁承担最终判断、如何持续执行、客户为何续费、哪些环节不是人工后台完成。当前仓库还不能用产品证据回答这些问题。

## 目标用户与当前适配

| ICP | 核心工作 | 当前支持 | 缺口 | 优先级 |
|---|---|---|---|---|
| 科技企业 Owner/CFO/行政 | 找机会、判断资格、准备申报、跟进截止日 | 基础画像、匹配列表、PDF | 资料导入、证据、case 协作、日历、通知、申报包 | P1 |
| 园区/孵化器 | 批量服务企业、看覆盖率、分配顾问、汇总成果 | 无批量租户/组合视图 | portfolio、批量扫描、顾问席位、成果看板、白标 | P1/P2 |
| 咨询/会计/知识产权机构 | 多客户工作台、材料清单、复核、交付 | 单租户单企业式体验 | 客户空间、模板、审批、权限、版本、计费 | P1 |
| 企业服务平台/API 客户 | 把匹配和执行嵌入现有系统 | 营销文案提到 API | API key、webhook、usage quota、SDK、审计、SLA 均缺失 | P2 |

## 端到端工作流覆盖

> 14 步 Agent 工作闭环的逐步代码证据、目标对象、API 和验收标准见 `11_AGENT_WORKFLOW_AUDIT.md`。本文件保留产品层摘要。

| 用户阶段 | 理想产品状态 | 当前代码状态 | 结论 |
|---|---|---|---|
| 1. 建立企业画像 | 表单 + 营业执照/财报/IP/人员资料导入，字段有来源与时效 | 基础表单 + `metadata_json` | 部分 |
| 2. 持续扫描机会 | 新政策摄取、去重、版本、地域/行业过滤、定时扫描 | 无 collector；手工写 Policy；匹配时即时算 | 缺失 |
| 3. 资格判断 | 硬门槛、证据引用、置信度、人工复核 | 两套引擎并存；主报告是启发式分数；独立 evaluator 未稳定 | 实验性 |
| 4. 找出材料缺口 | 对已有文档逐项映射政策要求 | 关键词生成通用清单 | 模拟 |
| 5. 生成申报材料 | 模板字段、引用来源、版本差异、审批 | `application_draft` 仍生成政策报告 | 缺失 |
| 6. 创建和执行任务 | durable workflow、负责人、截止时间、依赖、重试 | Task + BackgroundTasks | 部分且不可靠 |
| 7. 协作和复核 | 评论、指派、审批、修订闭环 | 可提交 RevisionRequest，但没有处理器 | 壳 |
| 8. 交付结果 | 可追溯 deliverable、下载、验收 | PDF 下载、accept | 部分 |
| 9. 持续跟踪 | 政策变更、申报状态、通知、续期 | “即将开放” | 缺失 |

## 价值主张与实际能力差距

### P0：必须立即修正的产品诚信问题

- 下载页把 Chrome v1.0.0 标记为 available，但仓库只有宣传页和两个图片资源，没有扩展包、manifest、发布链接或更新机制（`website/app/downloads/page.tsx:6-61`）。
- 安全页、隐私页对基础设施、加密、审计、备份、模型零保留和第三方评估作出确定性承诺，代码和数据室没有控制证据。
- “支付成功”“发票已生成”可由 demo 路由直接制造，不代表真实收入或交付。
- SmartAgent 将硬编码政策条件作为实时 AI 回答；即使真实 API 失败也静默回退，不向用户披露来源和时效（`website/components/SmartAgent.tsx:22-127,165-193`）。

处理原则：不是删除所有 demo，而是显式标记“示例数据/演示模式”，在 production build 中不可调用会改变商业状态的 demo API，并给每个事实性政策结论显示来源、发布日期和“需核验”。

### P1：阻碍成交和融资

- 没有一个完整的“资料 → 证据 → 判断 → 缺口 → 草稿 → 人审 → 交付”成功案例。
- 没有平台 Admin 和运营控制面，无法解释政策数据如何发布、错误如何纠正、客户如何开通。
- 没有企业协作：成员管理虽有 API 雏形，前端没有邀请、角色、审批、任务指派、通知。
- 收费模型混乱：SKU 迁移的报告价 ¥99、任务深度诊断 ¥99、SKU 深度诊断 ¥299、页面存在 ¥29/¥699 等不同价格。
- 没有订阅、用量、配额、合同、试用、退款实现，但条款宣称年付订阅和退款规则。
- 政策知识库未展示政策正文、来源、版本、适用地域、证据片段和更新状态，客户无法建立信任。
- 产品没有明确的人工复核工作台，无法安全承接高风险资格结论。

## 建议的首个可销售产品切片

不要同时做企业、园区、咨询机构三个完整产品。首个 8–12 周切片建议锁定：

**ICP：上海科技型中小企业的高企/专精特新/研发补贴机会诊断，由内部顾问或客户管理员复核。**

必须形成一个可以录像和复现的 Golden Journey：

1. 创建企业并上传营业执照、最近财务摘要、知识产权清单；
2. 系统解析并显示画像字段、来源页、置信度与待确认项；
3. 按已版本化政策自动扫描，显示候选机会；
4. 对一项政策逐硬门槛判断，引用政策原文和企业材料；
5. 将缺失项转成任务，指派负责人和截止日；
6. 基于模板生成申报初稿，所有关键字段可回溯；
7. 顾问审批/退回，系统记录修改历史；
8. 导出交付包，后续政策变化能重新评估并通知。

这条链路比增加更多营销页、模型选择器或下载端更能证明“AI 完成工作”。

## 信息架构建议

登录后应用应独立于营销站，一级导航建议为：

- 今日机会：新增、即将截止、待确认；
- 企业：画像、资料、证据、历史版本；
- 政策：来源、版本、适用范围、收藏；
- 申报项目：阶段、材料、任务、负责人、截止日；
- Agent 运行：执行步骤、证据、成本、异常、人工审批；
- 交付物：版本、审批、下载；
- 团队与设置：成员、角色、通知、数据保留；
- 账单：方案、用量、订单、付款和正规开票状态。

平台运营端应单独提供 policy publishing、tenant support、model/prompt/template version、failed jobs、billing reconciliation 和 audit search。

## 定价与包装

在可靠交付之前，不建议把单次 PDF 当核心商业模式。建议三层：

| 层级 | 价值 | 计费单位 | 进入条件 |
|---|---|---|---|
| Diagnostic | 单企业、单政策、有人审的资格诊断 | 按次/按企业 | 证据链和人审闭环可用 |
| Workspace | 持续扫描 + 多项目协作 + 材料与交付 | 席位 + 企业数 + Agent credits | durable workflow、通知、配额可用 |
| Portfolio/API | 园区/机构批量企业与集成 | 年度合同 + 企业数/API 用量 | Admin、SLA、审计、SSO/API key 可用 |

所有价格必须从服务端 Product/Price 版本读取；前端不再硬编码。早期可保留高触达服务，但需区分软件收入、实施收入与人工交付成本。

## Growth 与 Analytics 审计

### 当前状态

- 有 `analytics_events` 表和少量 report/payment/download 事件。
- 无匿名到注册的 acquisition attribution，无 demo request form、CRM、生命周期邮件、推荐机制或 A/B 实验。
- 首页、政策页和 SmartAgent 的行为不能组成可信漏斗；已登录政策页甚至会调用完整报告生成，制造 LLM 成本和重复机会记录。

### 建议北极星与漏斗

北极星指标：**每周被用户确认并进入执行的“有证据政策机会”数量**，而不是搜索次数或报告生成数。

核心漏斗：

1. Qualified account created；
2. Profile completeness ≥80% 且关键字段有来源；
3. First evidence-backed opportunity；
4. Eligibility reviewed；
5. Case activated；
6. Deliverable accepted；
7. 30/90 天持续扫描留存；
8. Expansion：新增企业/席位/项目。

每个事件需要 server-side authoritative event、tenant/user/case/version、数据字典和 PII 分类。客户端事件只能补充体验分析，不能作为收入或交付事实。

## 产品优先级

| 优先级 | 动作 |
|---|---|
| P0 | 下线生产 demo pay；修正虚假/无证据声明；资格结论强制人审；统一价格真源 |
| P1 | 完成 Golden Journey；文档摄取；证据视图；项目状态机；Admin；通知；可靠商业闭环 |
| P2 | 园区/服务机构 portfolio、多企业批处理、API/webhook、白标、订阅包装 |
| P3 | Chrome/桌面/移动客户端、更多行业 Agent、增长实验和自助 marketplace |

## 投资人可验证的产品证据包

融资演示前应准备：

- 3 个脱敏真实企业从原始资料到交付包的完整录像与时间成本对比；
- 每个 AI 结论的政策引用和企业证据；
- 人工复核修改率、严重错误率、任务成功率和单次成本；
- 30/90 天留存、重复扫描、被确认机会、进入申报和交付验收数据；
- 软件自动完成与人工服务步骤的明确边界；
- 价格、毛利、模型/OCR/人工成本和扩张路径。

## Phase 6 remediation status — 2026-09-04

The original P1 finding that Applications lacked an auditable human-review workspace is now
partially remediated in the codebase:

- Application now connects persisted eligibility, exact policy evidence, source-backed
  requirements, uploaded documents, a material-preparation Task, versioned drafts, comments, and
  activity in one tenant-scoped workspace.
- Readiness rules block review when hard materials, safe eligibility, or verified evidence are
  missing. Final Application approval requires Owner/Admin review of the latest artifact.
- Edit, regenerate, reject, and fix create or operate on explicit versions; previous drafts remain
  immutable and downloadable as DOCX, PDF, XLSX, or JSON.
- The right-side execution panel uses an explicitly named deterministic evidence engine. It does
  not claim LLM execution, file parsing, autonomous submission, or model quality that is not yet
  implemented.

This does not close the broader Golden Journey P1. Company-document parsing/OCR, durable
Application Agent execution, user assignment and notifications, official form templates, Admin
operations, evaluation evidence, and billing/enterprise packaging remain open in their planned
phases.

## Phase 7 remediation status — 2026-09-05

The original P1 finding that the product lacked a platform Admin and credible operating metrics is
now partially remediated:

- A persisted platform-admin authority is independent of tenant Owner/Admin roles, and all
  cross-tenant APIs enforce it on the backend.
- `/admin` exposes safe, paginated operating views for users, organizations, companies, execution,
  documents, policies, errors, billing, feedback, and analytics without returning stored secrets,
  raw payment payloads, document object keys, or Agent inputs/outputs.
- Server-owned, idempotent events cover the core acquisition-to-delivery milestones. Investor
  totals, model cost, paid revenue, system state, and the organization milestone funnel are
  calculated from database records with explicit definitions and currency boundaries.
- Tenant account stage makes PoC classification explicit; unknown organizations remain
  `unclassified` rather than being guessed.
- Missing evaluation, MRR, retention, and historical API-latency data is labelled unavailable. The
  Eval view displays `No evaluation data yet.` and does not substitute sample accuracy.

This does not close the broader enterprise-readiness P1. Reviewed Agent evaluations, durable
telemetry history, subscription/quota/invoice systems, cohort retention, CRM attribution, SSO,
support workflows, and audit-search operations remain open in later phases.

## Phase 8 remediation status — 2026-09-05

The original product-integrity gap around invisible or fabricated quality metrics is now partially
remediated:

- `/admin/evals` reports Accuracy, Citation Accuracy, Hallucination Rate, Pass Rate, Average
  Latency, and Average Cost only from persisted Eval Runs, with the applicable sample size and
  denominator visible.
- Each result can be traced through dataset version/checksum, target and scorer version, question,
  ground truth, actual answer, six quality dimensions, supporting evidence, and errors.
- Empty databases show `No evaluation data yet.`; repeated runs do not inflate the headline sample
  because comparison uses only the latest completed non-demo run per evaluation type.
- The bundled 11-case regression suite is clearly labelled synthetic and unreviewed. It does not
  make investor quality metrics available and is not represented as customer, model, or production
  performance.

This improves diligence readiness and release discipline but does not prove market-facing Agent
quality. The next quality milestone is a human-reviewed, double-annotated, adjudicated and frozen
benchmark drawn from the scoped launch domain, followed by live-model and end-to-end workflow
evaluation. Billing, quota, retention, commercial conversion, and enterprise controls remain Phase
9 work and must continue to use authoritative database records rather than inferred claims.
