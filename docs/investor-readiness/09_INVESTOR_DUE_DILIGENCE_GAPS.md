# 投资人技术尽调缺口

## 结论

当前仓库能证明团队已经构建了一个方向明确的 MVP，但不能证明它是稳定收费、企业安全、可规模化交付的产品。融资叙事应采用“我们识别并量化了风险，正在按 Gate 产品化”，而不是用现有页面数量推断生产成熟度。

最可能引发投资人暂停尽调的事项：

1. 产品中存在可直接伪造 paid/entitlement 的公开路由；
2. 迁移后的标准数据库与 ORM 不一致，核心任务链可能不能运行；
3. benchmark 显示资格准确率 43.8%、假阳性 28.6%；
4. 安全、备份、加密、零保留和第三方测试声明无证据；
5. 生产文档承认运行在个人 Mac 单点；
6. CI 位于 Git 仓库根不识别的嵌套位置，关键质量控制可能从未自动执行；
7. 核心“导入资料→证据→申报初稿”尚未实现。

## 尽调问题矩阵

| 领域 | 投资人/技术 DD 会问什么 | 当前仓库能证明 | 缺失证据 | 优先级 |
|---|---|---|---|---|
| Product | 客户真正完成了什么工作？ | 可创建画像、生成匹配/PDF、任务壳 | 脱敏真实 Golden Journey、验收、节省时间 | P1 |
| Market/ICP | 谁是最强 ICP，购买动机是什么？ | 页面同时面向企业/园区/机构 | 访谈、pipeline、win/loss、ICP 收敛 | P1 |
| Usage | 活跃、留存和使用深度？ | analytics 表和少量 events | 可核验 MAU/WAU、cohort、case activation、retention | P1 |
| Revenue | 收入是否真实、可对账？ | Order/Payment/Entitlement 模型 | provider 结算、银行流水、订单对账；demo 数据隔离 | P0 |
| Gross margin | 每个任务的模型/OCR/人工成本？ | AgentRun 有 token 字段 | 实际成本、人工分钟、毛利和扩张模型 | P1 |
| AI moat | 为什么比通用 LLM 好？ | policy engine、规则、benchmark | 达标 eval、独家数据、反馈闭环、质量趋势 | P1 |
| RAG/data | 数据来源、授权、更新和引用？ | Policy/source_url/crawled_at 字段 | source registry、采集授权、版本、lineage、freshness SLA | P1 |
| Reliability | 服务 SLA、故障和恢复？ | health、Compose、手册 | uptime、SLO、alerts、incident log、restore drill | P1 |
| Security | 如何隔离租户和保护资料？ | tenant_id filters、JWT、OSS prefix | RLS test、pentest、controls、DPA、IR evidence | P0/P1 |
| Compliance | PIPL/跨境/供应商如何处理？ | 法务页面声明 | 法律分析、RoPA、subprocessors、consent、DSR process | P0/P1 |
| Architecture | 能否支持 10x 客户？ | 模块化单体技术栈 | load test、queue、capacity/cost model、bottleneck plan | P1 |
| SDLC | 代码如何安全发布？ | nested CI 示例、release docs | 根级 required checks、branch protection、artifact provenance | P1 |
| IP | 代码/数据/Prompt 权属？ | 仓库本身 | 员工/外包 IP assignment、OSS 清单、数据许可 | P1 |
| Team | 谁负责 AI、平台、安全、产品？ | 无法从仓库确认 | owner map、bus factor、hiring plan、on-call | P2 |

## 数据室缺口清单

### 1. 产品与客户

需要新增：

- 当前 PRD、明确 ICP、非目标客户和 Golden Journey；
- 3–5 个脱敏客户案例：输入资料、系统步骤、人工步骤、输出、时间/成本、客户验收；
- 产品能力 truth table，区分 GA/Beta/Demo/Planned；
- 12 个月 roadmap，绑定客户证据而不是功能愿望；
- 客户访谈摘要、pipeline、试点合同/SOW、renewal/expansion 数据；
- 功能声明和证据 register。

### 2. 架构与工程

- current-state/target-state 架构图和 ADR；
- API OpenAPI snapshot、数据字典、ERD、workflow 状态机；
- dependency/SBOM、OSS license review；
- root CI 运行历史、测试覆盖、release artifacts、branch protection；
- 性能测试、容量模型、主要瓶颈和成本曲线；
- technical debt register、Owner、期限和风险接受。

### 3. AI、RAG 与数据

- 模型/provider/prompt/embedding/evaluator version registry；
- dataset card：来源、许可、标注流程、分桶、泄漏控制、参考日期；
- eval 报告历史，不只保留最佳版本；
- retrieval、citation、hard-gate、hallucination、human edit 指标；
- policy source registry、更新频率、失败率、版本 lineage；
- 人工复核 SOP、错误升级和高风险 policy；
- 模型供应商 DPA、retention/training/region 证明。

### 4. 安全、隐私与合规

- data flow diagram、data inventory/classification、RoPA；
- access control matrix、tenant isolation test report；
- threat model、secure SDLC、vulnerability management；
- independent penetration test 与 remediation；
- secrets/KMS/IAM/backup/DR 控制证据；
- incident response plan、tabletop 和 incident history；
- subprocessor list、DPA、跨境法律意见；
- DSR、retention/deletion、账号关闭、legal hold 流程；
- 对外安全声明逐条证据。

### 5. 运营与可靠性

- 实际生产 topology、cloud inventory、owner、region、环境隔离；
- uptime/SLO/dashboard/alerts/on-call；
- deployment、rollback、migration、backup、restore runbooks；
- 最近一次 restore 演练和 RPO/RTO 结果；
- incident/postmortem 记录；
- vendor outage 和模型/payment failover 方案。

### 6. 商业和财务技术证据

- SKU/PriceVersion、合同价格和前端展示的一致性；
- 真实付款与 demo 数据隔离说明；
- provider settlement ↔ Payment ↔ Order ↔ Entitlement 对账；
- refund、chargeback、tax invoice 流程；
- usage/model/OCR/storage/human cost 到客户/任务的归因；
- ARR/MRR、软件收入与服务收入定义和可复算 SQL。

### 7. IP 与组织

仓库无法确认，需公司层补充：

- 创始人、员工、顾问、外包的发明/代码/Prompt/数据 IP 转让；
- 第三方代码和数据 license；
- 商标、域名、软件著作权/专利状态；
- GitHub/云/支付/域名/邮箱等关键账号公司所有权；
- bus factor、权限离职流程和紧急联系人。

## 文档一致性缺口

| 冲突 | 证据 | 处理 |
|---|---|---|
| 后端 README 说无真实支付/前端，仓库已有相关代码 | `yance-ai/README.md:1-16,90` | README 分 Current/Experimental/Planned 并自动关联 release |
| 运维手册说公共注册已移除，代码和前端仍有注册 | `PRODUCTION_OPS.md:67` vs `auth.py:96-150` | 以 production feature flag 和运行测试证明 |
| 生产既描述 Mac，又描述 ECS/RDS、腾讯云香港 | 多份运维/安全文档 | 单一 current topology，target architecture 单独标注 |
| 版本有 0.1.0/0.2.0/报告 V2.2 | pyproject/VERSION/ops/benchmark | 分 app release、engine version、data version，不混用 |
| 隐私说 Cookie 登录，代码是 localStorage | privacy vs api.ts | 修实现和文案 |
| 条款有年付订阅/退款，模型无 Subscription/Refund | terms vs data model | 未上线条款移除或实现后再声明 |

## 建议融资叙事

可可信表达：

> Yance 已完成领域模型、政策匹配、证据型资格引擎和任务交付的 MVP 骨架。内部基准暴露了硬门槛和假阳性问题，我们没有把未达标模型包装成自动决策。下一阶段资金用于把资料摄取、证据链、持久工作流、人工审批和企业安全做成一个可重复交付的 Golden Journey。

暂不建议表达：

- “已具备企业级安全/零保留/全量审计/灾备”；
- “AI 已自动完成申报”；
- “Chrome 插件已发布”；
- “支付、订阅和开票闭环成熟”；
- “准确率领先通用模型”；
- 将 seed/demo order 当收入或客户验证。

## 融资前最小证据包

### 必须完成（P0/P1）

1. P0 全部关闭的测试与 release 记录；
2. root CI 绿灯和可复现 staging deployment；
3. 3 个脱敏真实 Golden Journey；
4. 至少 100 条冻结评测集和按风险分桶结果；
5. 真实支付/权益/对账证明，demo 数据隔离；
6. 租户隔离测试和独立渗透测试摘要；
7. 数据流、供应商、保留/删除和备份恢复证据；
8. 真实产品漏斗、客户反馈、单任务成本和毛利模型。

### 可以随后补充（P2）

- 99.9% SLA、SSO/SCIM、跨地域 HA；
- 大规模 API/portfolio 案例；
- SOC 2/ISO 27001 等认证。不要在流程未建立前购买徽章替代安全工程。

## DD Red Flag 处置状态模板

每个重要问题应在数据室用同一结构记录：

```text
Risk ID / discovered date / severity
Customer and business impact
Root cause
Compensating control
Remediation owner / target date
Code change / test / deployment evidence
Residual risk / approver
```

这种透明的闭环记录比“无已知问题”的叙述更能建立天使轮投资人信任。
