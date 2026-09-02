# Agent 工作闭环专项审计

审计日期：2026-09-02

目标：将当前“输入信息 → 匹配报告”升级为“企业资料 → 证据判断 → 申报执行 → 人审 → 多格式交付 → 下一步行动”的 14 步闭环。

## 结论

当前产品只形成了一个不稳定的短链路：

```text
注册/登录
  → 自动创建 Tenant 和基础 Company
  → 手工填写部分画像
  → 全局政策向量匹配 + 启发式评分
  → 创建 Task
  → 同一报告管线生成 PDF
  → 验收/修改请求壳
  → 规则式 Next Best Action
```

目标 14 步中：

- 2 步基本存在但不完整：注册/登录、基础企业画像；
- 5 步只有局部实现或演示壳：Organization、Opportunity Scan、AI Execution、Human Review、Deliverable、Next Best Action；
- 7 个关键能力未形成产品闭环：多格式资料导入、AI 结构化解析、四态资格引擎、证据引擎、可靠 Gap Analysis、Application Workspace、版本化多格式交付。

因此当前不能把 Task 页面等同于 Application Workspace，也不能把匹配分等同于 Eligibility，不能把关键词材料清单等同于 Evidence/Gap Engine。

## 状态定义

- **存在**：前后端主链路可用，数据持久化且有明确契约；
- **部分**：有可复用实现，但字段、状态、证据或 UI 不完整；
- **壳**：页面/表/API 名称存在，实际工作没有完成；
- **缺失**：没有实现；
- **阻断**：已有实现存在 P0 安全、数据或可信度问题，不能进入生产闭环。

## 14 步覆盖矩阵

| Step | 目标 | 当前状态 | 代码证据 | 关键差距 | 优先级 |
|---:|---|---|---|---|---|
| 1 | 注册 / 登录 | 部分 | `auth.py:96-187`；`website/app/login/page.tsx` | 无邮箱验证、重置密码、会话撤销、MFA；登录无限流；JWT 在 localStorage | P1 |
| 2 | Organization / Workspace | 部分 | 注册时自动创建 Tenant；`tenants.py:15-52` | 用户不能显式创建/切换 Organization；没有 Workspace 实体、邀请、成员管理 UI、组织设置 | P1 |
| 3 | Company Profile | 部分 | `onboarding/page.tsx:7-106`；`Company` + `metadata_json` | 只覆盖部分字段；成立时间不是日期；资质混成数组；无数据来源、版本、确认和完整度 | P1 |
| 4 | PDF/DOCX/XLSX/CSV/TXT/URL 导入 | 壳 | `documents.py:37-90` 仅 OSS presign/exists | 无上传 UI、URL import、格式 allowlist、大小校验、malware、下载、解析状态 | P1 |
| 5 | AI 解析 Company Intelligence | 缺失 | Document 最终状态只到 `uploaded` | 无 OCR/parser/chunker/extractor、结构化事实、来源 span、冲突与确认 | P1 |
| 6 | Policy / Opportunity Scan | 部分且阻断 | `report/matcher.py:36-234` | 只有 Policy；无采集/调度/去重/版本；赛事、融资、园区、券等没有统一 Opportunity Source | P1 |
| 7 | 四态 Eligibility Engine | 部分且阻断 | `policy_engine` 输出三态；独立于主报告 | 缺 `Potentially Eligible`；主产品仍展示启发式匹配分；存在硬门槛软化 P0 | P0 |
| 8 | Evidence Engine | 壳 | `evidence_json` 只有分数组成/材料；evaluator 有 quote 字段 | 缺来源版本、发布日期/有效期、地区、原文 span、企业数据来源；关键结论可无来源 | P0/P1 |
| 9 | Gap Analysis | 壳 | matcher 按关键词生成 `missing_materials` | 不区分已有/缺失、hard/soft、事实/材料、负责人/截止日；未和文档事实比对 | P1 |
| 10 | Application Workspace | 缺失 | `Application` 只有 CRUD；Task 页面是单报告视图 | 没有 10 个指定 tab、case 状态机、材料关系、timeline、activity、comments、export | P1 |
| 11 | AI Execution | 壳 | 三种 Task 运行同一 match + PDF 管线 | 没有九类可选择 action、tool contract、持久 workflow、审批点、失败恢复 | P1 |
| 12 | Human Review | 壳 | `accept` + `RevisionRequest` | 无 Approve/Reject/Edit/Regenerate；revision 无处理器；无 reviewer、reason、diff、审计 | P1 |
| 13 | DOCX/PDF/XLSX/JSON 交付与版本 | 部分且阻断 | PDF 可下载；Deliverable version 固定 1 | 无 DOCX/XLSX/JSON；PDF 输入未转义；内容未持久；无 immutable version/diff/hash | P0/P1 |
| 14 | Next Best Action | 部分 | `tasks.py:298-319` | 规则只看分数/材料关键词；无资格状态、公司目标、已完成任务、政策路径和用户反馈 | P2 |

## Step 1：注册与登录

### 当前路径

Public register 一次事务创建 Tenant、Owner 和默认 Company；login 返回 access token。这个起点可以保留。

### 目标验收

- 注册必须记录条款/隐私版本和同意时间；
- 邮箱验证完成后才允许上传敏感资料；
- 支持忘记/重置/变更密码、session 列表、单设备/全设备退出；
- 登录和注册使用共享限流，失败行为可告警；
- Web 使用 HttpOnly session，不把 bearer token 放 localStorage；
- API 返回稳定的 `onboarding_state`，而不是由页面猜测下一步。

## Step 2：Organization / Workspace

### 建议层级

```text
Organization (现 Tenant)
  ├─ Membership / Role / Billing / Security policy
  └─ Workspace
       ├─ Companies
       ├─ Knowledge sources
       ├─ Opportunity scans
       └─ Application workspaces
```

早期可在注册时创建默认 Workspace，但必须保留显式实体。Organization 是合同、成员和账单边界；Workspace 是业务数据和项目协作边界。不能让“Tenant”和“Application Workspace”使用同一个模糊 workspace 概念。

### 目标验收

- 创建、命名、切换和归档 Workspace；
- Owner/Admin 可邀请成员并设置角色；
- 所有 Company/Document/Opportunity/Application 同时绑定 organization 和 workspace；
- API/数据库 tenant + workspace scope 自动化隔离。

## Step 3：Company Profile

### 当前字段覆盖

| 目标字段 | 当前数据 | 判断 |
|---|---|---|
| 企业名称 | `Company.name` | 已有 |
| 所属行业 | `Company.industry` | 已有，未标准化 |
| 注册地址 | province/city + metadata district | 部分，无完整地址 |
| 成立日期 | metadata `founded_year`/年龄选项 | 不满足日期和时效 |
| 企业规模 | metadata `scale` | 部分 |
| 营收阶段 | 无 | 缺失 |
| 融资阶段 | 报告读取 metadata，onboarding 不填写 | 缺失主流程 |
| 高新企业情况 | qualifications 数组 | 不足：无状态/证书/有效期 |
| 科技型中小企业情况 | qualifications 数组 | 不足 |
| 专精特新情况 | qualifications 数组 | 不足 |
| 知识产权 | `ip_count` | 不足：无类型、编号、权利人、有效期 |
| 核心产品 | 无主流程字段 | 缺失 |
| 研发情况 | 两个比例 | 部分，无年度和来源 |
| 人才情况 | 研发人员比例 | 部分 |
| 项目情况 | 无 | 缺失 |
| 当前需求 | policy_needs | 部分，过度政策化 |

### 目标数据原则

- `Company` 保存稳定身份；`CompanyProfileVersion` 保存不可变快照；
- 每个 `CompanyFact` 有 typed value、unit、effective date、source、confidence 和 verification status；
- 用户手填、文件抽取、外部数据和人工复核必须可区分；
- 新资料不会静默改写已生成的 Eligibility/Deliverable。

## Step 4–5：资料导入与 Company Intelligence

### 支持矩阵

| 类型 | 导入 | 解析 | 最低安全控制 |
|---|---|---|---|
| PDF | OSS API 壳 | 无 | magic bytes、页数/大小、OCR sandbox、恶意 PDF |
| DOCX | OSS API 壳 | 无 | ZIP bomb、外部关系、宏拒绝 |
| XLSX | OSS API 壳 | 无 | sheet/cell 上限、公式不执行、外部链接拒绝 |
| CSV | OSS API 壳 | 无 | encoding、行列上限、CSV formula injection |
| TXT | OSS API 壳 | 无 | encoding、大小和控制字符 |
| URL | 无 | 无 | SSRF、DNS rebinding、redirect、private IP、响应大小 |

### 目标 pipeline

```text
Upload/URL request
  → quarantine
  → validate + malware scan
  → DocumentVersion
  → sandbox parse/OCR
  → chunks/spans
  → typed fact extraction
  → validation/conflict detection
  → user confirmation
  → CompanyProfileVersion publish
```

UI 必须显示 `uploaded / scanning / parsing / extracting / needs_review / ready / failed`，不能在文件存在时就声称 AI 已理解。

## Step 6：Policy / Opportunity Scan

### 领域修正

`Policy` 不能承载所有机会。建议：

```text
OpportunitySource
OpportunityProgram
  type = policy | subsidy | competition | talent_program |
         science_project | financing | park_resource |
         compute_voucher | model_voucher | qualification
OpportunityProgramVersion
OpportunityCriterion
OpportunityCandidate
ScanRun
```

高企、科技型中小企业、专精特新属于 `qualification`；补贴/券/赛事/人才/融资/园区分别保留类型。所有来源必须版本化并具有 canonical URL、发布机构、发布日期、有效期和地域。

### 目标验收

- 支持手工发布和至少一个可审计的数据采集源；
- 扫描可手工触发和定时触发；
- 幂等、不重复创建 Candidate；
- 保存 profile version、program version、engine version；
- UI 将“相关机会”与“资格结论”明确分开。

## Step 7：Eligibility Engine

唯一允许对外的状态枚举：

```text
ELIGIBLE
POTENTIALLY_ELIGIBLE
NOT_ELIGIBLE
NEED_MORE_INFORMATION
```

### 状态规则

- `NOT_ELIGIBLE`：至少一个已验证 blocking criterion FAIL；
- `NEED_MORE_INFORMATION`：至少一个 blocking criterion 缺失事实或来源不足，且没有已验证 hard FAIL；
- `POTENTIALLY_ELIGIBLE`：所有已解析 hard gate 均 PASS，但仍有非阻断差距、未最终确认材料或低置信度事实；
- `ELIGIBLE`：所有 hard gate PASS、关键事实有证据、policy version 有效，并经所需 human approval；
- 未解析条件默认 `NEED_MORE_INFORMATION`，禁止默认为 PASS。

状态由确定性 Gate 聚合，LLM 不得直接指定 overall result。当前硬门槛正则缺陷必须先修复。

## Step 8：Evidence Engine

每个重要结论必须持久化以下字段，而不是只在自然语言里出现：

```text
conclusion
criterion_result
evidence_text
policy_source_id / program_version_id
policy_clause
published_at
valid_from / valid_until
applicable_region
original_quote
original_span_id
company_fact_id / document_span_id
data_source_type
confidence
extractor / rule / model / prompt version
review_status / reviewer
```

### 强制规则

- 没有 policy/program source 的政策结论不得展示为事实；
- 没有 company fact source 时必须标记 `user_asserted` 或 `unverified`；
- quote 必须能跳转到原文位置；
- 过期/被替代版本必须阻止新的 ELIGIBLE；
- confidence 不是装饰分数，需要校准数据和阈值。

## Step 9：Gap Analysis

Gap 需要是可执行对象：

```text
GapItem
  category = criterion | fact | document | validation
  severity = blocking | required | recommended
  current_state
  required_state
  evidence
  remediation
  owner
  due_at
  status
```

输出固定分组：已具备、缺失硬门槛、缺失必要材料、待核验信息、建议增强项、下一步动作。关键词检测只能作为候选，不能自动断言材料缺失。

## Step 10：Application Workspace

用户点击“开始申报”后，必须创建数据库中的 `ApplicationWorkspace`，不能只跳转报告页。

### 10 个指定视图

| Tab | 核心对象 | 验收 |
|---|---|---|
| Overview | ApplicationWorkspace | 项目、企业、机会、Owner、状态、截止日 |
| Eligibility | EligibilityAssessment/Criteria | 四态结论与逐条件结果 |
| Evidence | EvidenceItem | 双向打开政策原文和企业数据 |
| Required Documents | Requirement/Gap/Document link | required/received/valid/missing |
| Generated Documents | DeliverableVersion | 格式、版本、审核状态、下载 |
| Tasks | WorkspaceTask | assignee、due、dependency、status |
| Timeline | Milestone/Deadline | 政策窗口和内部截止日 |
| Activity | append-only ActivityEvent | actor、time、change、trace |
| Comments | Thread/Comment/Mention | 可解析对象和审计 |
| Export | ExportJob | DOCX/PDF/XLSX/JSON 打包状态 |

建议 URL：`/applications/[applicationId]`，内部 tab 用 search param 或子路由；营销与应用必须使用不同 App Router route group/layout。

## Step 11：AI Execution

> Agent 分工、统一 Harness、Tool Registry、执行状态机和 Verification Loop 的详细规格见 `12_AGENT_ARCHITECTURE_RAG_EVAL_SPEC.md`。

每项 AI 能力应是 versioned action，不是任意聊天：

| Action | 输入 | 输出 | 必须 Gate |
|---|---|---|---|
| 材料检查 | requirement + documents | status/findings | evidence links |
| 申报资格分析 | profile version + program version | assessment | deterministic final gate |
| 材料清单生成 | criteria + template | requirements | source clause |
| 缺口分析 | assessment + documents | GapItems | hard/soft classification |
| 文档草拟 | template + approved facts | draft | citation + human review |
| 政策解释 | version + query | structured explanation | source-only |
| 企业画像补全 | parsed facts | proposed profile changes | user approval |
| 文件摘要 | document version | summary | document spans |
| 信息提取 | schema + document | typed facts | confidence + provenance |
| 申报材料生成 | approved facts + template | deliverable versions | human approval |

所有 action 通过持久 WorkflowRun/StepRun 执行，记录版本、证据、token/cost、错误和审批，不由 Web BackgroundTasks 承担。

## Step 12：Human Review

Review 是独立状态机：

```text
DRAFT → IN_REVIEW → APPROVED
                  ↘ REJECTED
                  ↘ CHANGES_REQUESTED → REGENERATING → IN_REVIEW
```

四个用户动作：

- Approve：记录 reviewer、时间、对象 hash、意见；
- Reject：必须给 reason，不允许继续导出为 final；
- Edit：创建新版本并保留 diff/actor；
- Regenerate：基于明确 instruction 创建新 Agent run 和新版本。

同一生成者是否可以审批应由 organization policy 控制；高风险客户可要求 four-eyes review。

## Step 13：Deliverable

### 格式职责

- DOCX：可编辑申报初稿和说明；
- PDF：锁定的人审交付版；
- XLSX：材料清单、资格矩阵、任务/时间表；
- JSON：API/数据室导出，附 schema/version。

### 版本要求

每个 `DeliverableVersion` 保存 content hash、source snapshot、generator/template/model version、created_by、review status 和 supersedes ID。已批准版本不可覆盖；任何 Edit/Regenerate 创建新版本。

PDF renderer 的 HTML 注入/SSRF P0 关闭前，不允许把用户数据生成的 PDF 作为生产交付。

## Step 14：Next Best Action

NBA 输入至少包括：

- 当前 CompanyProfileVersion；
- 所有 Candidate/Assessment/Gap；
- Application 状态、截止日、已完成任务；
- 用户当前需求和 organization policy；
- 历史推荐的接受/拒绝反馈。

输出必须是结构化对象：`action_type`、`title`、`reason`、`evidence_ids`、`priority`、`due_at`、`estimated_effort`、`cta`。例如科技型中小企业主要门槛通过且高企条件接近时，才可推荐准备高企；不能仅凭一个匹配分自动推销 SKU。

## 推荐 API Surface

```text
POST   /organizations
POST   /workspaces
GET    /workspaces/{id}/members

POST   /workspaces/{id}/companies
GET    /companies/{id}/profile
POST   /companies/{id}/profile/versions

POST   /companies/{id}/documents/presign
POST   /companies/{id}/sources/url
GET    /documents/{id}/processing-status
POST   /companies/{id}/intelligence-runs
POST   /company-profile-versions/{id}/publish

POST   /companies/{id}/opportunity-scans
GET    /scan-runs/{id}
GET    /companies/{id}/opportunity-candidates

POST   /opportunity-candidates/{id}/assessments
GET    /assessments/{id}/criteria
GET    /assessments/{id}/evidence
GET    /assessments/{id}/gaps

POST   /opportunity-candidates/{id}/applications
GET    /applications/{id}
POST   /applications/{id}/agent-actions
POST   /applications/{id}/reviews
POST   /applications/{id}/comments
POST   /applications/{id}/exports
GET    /applications/{id}/next-actions
```

所有创建型接口需要 idempotency key；所有读取强制 organization/workspace scope；长任务返回 run ID 和可恢复状态。

## 端到端验收场景

### Golden Journey

1. 新用户注册并验证邮箱；
2. 自动创建 Organization 和默认 Workspace；
3. 填写 16 类画像字段；
4. 上传 PDF/DOCX/XLSX/CSV/TXT，并导入一个公开 URL；
5. 文件经过安全扫描与解析，用户确认提取事实；
6. 发布 CompanyProfileVersion；
7. Scan 发现至少两种不同类型机会；
8. 一项输出 POTENTIALLY_ELIGIBLE，一项 NEED_MORE_INFORMATION；
9. 每个条件都能打开政策原文和企业证据；
10. 用户查看 blocking gaps 并点击“开始申报”；
11. Workspace 生成材料任务和初稿；
12. Reviewer Reject 第一版、Edit/Regenerate 第二版、Approve 第三版；
13. 导出 DOCX/PDF/XLSX/JSON，历史版本仍可查；
14. 系统基于已批准结果生成有证据的 NBA。

### 必测负向场景

- 其他租户不能读取任何 document/evidence/application/export；
- 恶意 URL、私网地址、超大/伪装文件和 HTML/PDF 载荷被拒绝；
- 政策过期、硬门槛 FAIL、来源缺失不能输出 ELIGIBLE；
- worker 在解析、判断、生成任一步骤退出后可恢复且不重复；
- Reject 的版本不能下载为 final；
- 同一支付/任务/export 请求重复提交不产生重复权益或版本。

## 实施优先级

### P0：可信度和安全 Gate

- 修 Eligibility hard gate、Evidence numeric validator、PDF renderer；
- 冻结“无来源政策结论”和生产 demo payment；
- 修 schema drift 和跨租户边界。

### P1-A：Steps 1–5

- 安全 session、Organization/Workspace、完整画像字段；
- 安全 ingestion、Company Intelligence、profile version/事实来源。

### P1-B：Steps 6–10

- 泛化 Opportunity、版本化 source、四态 assessment、Evidence/Gap、Application Workspace。

### P1-C：Steps 11–13

- durable Agent actions、Human Review、版本化 DOCX/PDF/XLSX/JSON。

### P2：Step 14 与增长

- 有证据 NBA、反馈学习、通知、portfolio/API 和 usage packaging。

## 发布判定

“完整 Agent 工作闭环”不能由页面数量判定。只有以下事实同时成立才可标记 GA：

- 14 步 Golden Journey 自动化 E2E 通过；
- 关键判断 100% 有可打开来源；
- 四态 Eligibility 状态机和人审 Gate 生效；
- 所有长任务可恢复、幂等；
- 四种交付格式和版本历史可验证；
- 跨租户和恶意输入测试通过；
- AI 质量达到 `05_AGENT_RAG_AUDIT.md` 的分桶发布阈值。
