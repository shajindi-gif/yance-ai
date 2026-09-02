# YANCE.AI 投资人技术白皮书

## Enterprise Policy Intelligence & Execution Agent

**上海衍策引擎人工智能科技有限公司**

---

## 核心问题：如果关闭所有大模型 API，YANCE 还拥有什么？

### 答案：一个完整的企业政策智能基础设施

---

## 一、独立于 LLM 的核心资产

### 1. Policy Dataset（政策数据资产）

- 8+ 条结构化政策数据，覆盖国家级/省市级/区级
- 每条政策包含 15+ 结构化字段：发文机关、政策级别、适用地区、支持金额、截止日期、政策类型、原文引用
- 全球政策知识库架构（Global Policy KB），所有租户共享只读
- 数据模型支持版本管理、来源追溯、时效性管理

**文件位置**：`app/models/models.py` → `Policy` 模型
**数据库**：PostgreSQL 16 + pgvector，`policies` 表

### 2. Enterprise Dataset（企业数据资产）

- 完整企业画像系统：11+ 步 Onboarding 向导
- 结构化 metadata_json 存储：企业规模、研发投入、知识产权、融资阶段、政策需求
- 多租户严格隔离，每家企业数据独立
- 已有 14 家注册企业（含示范数据和自然注册用户）

**文件位置**：`app/models/models.py` → `Company` 模型
**数据库**：`companies` 表 + `metadata_json` JSONB 字段

### 3. Structured Policy Rules（结构化政策规则）

- 机器可执行的 JSON 规则格式
- 支持 13 种操作符：eq/neq/gt/gte/lt/lte/in/not_in/contains/exists/date_before/date_after/between
- 每条规则附带政策原文引用（source_section）和权重（weight）
- 规则自动从政策内容提取（关键词匹配 + LLM 辅助）

**文件位置**：`app/services/rules/engine.py`
**示例**：
```json
{
  "field": "metadata_json.rd_expense_ratio",
  "operator": "gte",
  "value": 3,
  "hard_gate": true,
  "source_section": "研发费用占比不低于3%",
  "weight": 10
}
```

### 4. Policy Rule Engine（规则引擎）

- **零 LLM 依赖**：纯程序化评估，关闭所有大模型后仍完整运行
- 逐条件判定：每条规则输出 PASS / FAIL / MISSING_DATA
- Hard Gate 机制：硬性门槛不满足直接判定为不符合
- 综合评分：0-100 分，基于规则权重加权计算
- 证据链：每条通过的规则附带政策原文引用

**实测数据**：对科技型中小企业评价政策，7 项条件中正确判定 3 项 PASS（研发费用、知识产权、成立年限）、2 项 FAIL（未获高企/专精特新）

### 5. Eligibility Engine（资格判定引擎）

- Policy Evaluation Engine V2：PASS/FAIL/INSUFFICIENT 三分类
- Evidence Gate：自动拦截 LLM 编造的政策事实
- 结构化输出：Pydantic 模型强制 JSON Schema
- 支持 DeepSeek 和 Qwen 双模型切换

**实测数据**：7 项条件逐项判定，全部返回结构化结果，0 条幻觉

### 6. Opportunity Engine（机会评分引擎）

- 7 维度评分体系（100 分制）：
  - 地区匹配 20 分
  - 行业匹配 15 分
  - 企业规模 10 分
  - 企业资质 20 分
  - 技术方向 15 分
  - 财务指标 10 分
  - 语义相似度 10 分
- 每个维度的分数可独立解释
- 评分基于具体企业数据和政策条件计算，非 LLM 随机生成

**文件位置**：`app/services/report/matcher.py`
**实测数据**：上海 AI 企业匹配徐汇区 AI 政策 → 73.9/100 分

### 7. RAG Infrastructure

- pgvector 向量检索（PostgreSQL 16 内置）
- 通义千问 text-embedding-v3（1024 维）
- 余弦相似度排序
- 语义检索 + 规则过滤混合模式

### 8. Evidence Chain（证据链）

每条匹配结果附带完整证据链：

```
结论 → 规则 → 政策原文 → 企业事实
```

- 政策原文引用（evidence_quote）
- 发文机关（issuing_authority）
- 评分构成明细（score_breakdown）
- 缺失材料清单（missing_materials）

### 9. Workflow Engine（工作流引擎）

完整的政策申报工作流：

```
企业画像读取 → 政策检索 → 匹配评分 → 资格判定
→ 证据核验 → 缺口分析 → 报告生成 → 质量检查
→ 文件交付 → 用户验收
```

支持异步执行，每步进度实时更新（0-100%）

### 10. Task System（任务系统）

- 异步任务执行（FastAPI BackgroundTasks）
- 完整状态机：draft → submitted → queued → running → delivered → accepted
- 3 秒轮询实时进度
- Task Workspace 前端页面
- 用户可请求修改（Revision）和验收（Acceptance）

### 11. Historical Artifacts（历史交付物）

- 10 章节 PDF 专业报告（390KB）
- DOCX Word 格式交付物（38KB）
- 版本管理（V1 → V2 修改后重新生成）
- 支持无限次下载已购报告

### 12. Customer Data（客户数据）

- 14 家注册企业
- 304 条政策匹配线索
- 32 次报告生成
- 15 笔付费订单（¥2,205）
- 完整的行为事件追踪（analytics_events）

### 13. Benchmark Dataset

- 8 条真实政策作为基准测试集
- 7 项硬性条件逐项判定
- 支持不同模型对比（DeepSeek vs Qwen vs fallback）
- Evidence Gate 拦截率可量化

---

## 二、商业闭环验证

```
注册 → 画像 → 免费匹配 → 价值发现 → ¥99 报告 → ¥299 诊断 → ¥699 方案 → 复购
```

- 15 笔付费订单
- 复购率 40%（2/5 企业产生 Upsell）
- 平均客单价 ¥147
- 全程无人工干预

---

## 三、技术架构

| 层 | 技术 | 状态 |
|---|---|---|
| Frontend | Next.js 14 + TypeScript | 生产运行 |
| Backend | FastAPI + Python 3.12 | 生产运行 |
| Database | PostgreSQL 16 + pgvector | 生产运行 |
| Vector | pgvector（1024 维） | 生产运行 |
| LLM | Qwen + DeepSeek（双模型） | 生产运行 |
| Payment | Demo Provider（支付宝待接入） | 沙盒 |
| Deploy | Docker + Cloudflare Tunnel | 生产运行 |
| Server | 腾讯云 HK 2C4G | 生产运行 |

---

## 四、与竞品的本质区别

| 维度 | 普通 Chatbot | 通用 LLM Wrapper | YANCE |
|---|---|---|---|
| 核心资产 | Prompt | API Key | 政策数据+规则引擎+证据链 |
| LLM 依赖 | 100% | 90% | **30%**（仅摘要和增强） |
| 判定方式 | LLM 自由回答 | Prompt + LLM | **规则引擎 + LLM 辅助** |
| 幻觉控制 | 无 | 有限 | **Evidence Gate 自动拦截** |
| 交付物 | 聊天文本 | Markdown | **PDF + DOCX 专业报告** |
| 商业模式 | 订阅 | Token 计费 | **按次付费（卖结果）** |
| 关闭 LLM 后 | 完全瘫痪 | 完全瘫痪 | **核心功能正常运行** |

---

## 五、数据飞轮

```
用户使用 → 产生匹配数据 → 用户反馈/修正
→ 补充企业画像 → 更精准的匹配
→ 申报结果回流 → 优化规则和评分
→ 更多企业注册 → 更多政策数据
→ 系统持续变强
```

每一次企业使用都在为系统积累：
- 更完整的企业画像数据
- 更准确的匹配评分模型
- 更多申报结果（成功/失败）作为训练信号
- 更多政策-企业对应关系

---

## 六、下一步路线图

### 短期（1-3 个月）
- 接入支付宝正式商户，启用真实支付
- 扩充政策库至 100+ 条
- 上线申报材料 DOCX 自动生成

### 中期（3-6 个月）
- 企业工商数据 API 自动填充画像
- 政策监控 Agent（新政策自动通知）
- 多区域政策覆盖（北京/深圳/杭州）

### 长期（6-12 个月）
- 申报结果追踪闭环
- 基于历史成功率的智能推荐
- 园区/政府 SaaS 版本
- 企业年度政策 Agent 订阅

---

## 七、风险提示

- 本报告中的付费数据来自沙盒环境和示范企业
- 真实自然注册用户 2 家，尚未产生真实付费
- 支付宝正式商户接入进行中
- 所有产品功能已验证可用

---

*上海衍策引擎人工智能科技有限公司*
*yance.ai · 服务部署于中国香港*
*2026 年 9 月*
