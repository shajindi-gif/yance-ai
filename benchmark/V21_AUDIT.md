# Yance Policy Evaluation Engine — V2.1 冲刺前审计（V21_AUDIT）

审计时间：2026-08-31 20:50 (GMT+8)
审计对象：`/Users/shajindi/Desktop/yance-backup/yance/yance-ai/app/services/policy_engine/`（schemas.py, evaluator.py）、`app/api/routes/policy_engine.py`、`app/services/llm/router.py`
审计人：独立 Benchmark/QA Agent。本审计只读代码，未修改任何文件。

## 0. 实现确认【事实】
- Policy Evaluation Engine V2 真实存在：`POST /policy-engine/evaluate`（tenant 鉴权 + Policy/Company 表读取 → `evaluate_policy()`）。
- 流程：Step1 LLM 提取硬性条件 → Step2 LLM 逐项判定（PASS/FAIL/INSUFFICIENT）→ Step3 Evidence Gate（正则数字校验）→ Step4 材料缺口/风险/推荐。
- LLM Router 已接入 deepseek / qwen / openai / claude / mock，OpenAICompatible。

## 1. 关键缺陷清单（按风险排序）

### D1【高危】无 Deterministic Evaluator —— 所有数学判断交给 LLM
研发占比（480万/1000万）、分档比例（<5000万→5%）、科技人员占比（3/18=16.7%）等全部由 LLM 心算。Benchmark V1 已证实这是数字型门槛的主要失败来源（S12 画像矛盾就是靠 LLM 自觉才被发现）。
→ 修复：新增 `deterministic.py` 程序化 evaluator（比较运算由 Python 执行），LLM 判定与程序计算冲突时以程序为准。

### D2【高危】Evidence Gate 会误杀合法的企业事实数字
`validate_evidence()` 把 reason 中的所有数字与「政策原文数字集合」对比。企业自身数字（研发50万、员工18人、16.7%）不在政策原文中，会被错误替换为「[数据待验证]」并把 confidence 压到 0.3。即：Gate 的意图（拦截政策幻觉）是对的，但实现把「企业事实引用」和「政策条件断言」混为一谈。
→ 修复：Gate 改为只校验「门槛/比例/金额类断言」（threshold assertions），企业事实字段（enterprise_fact）豁免；并对照 frozen policy 全文而非 3000 字截断。

### D3【高危】overall_result 聚合由 LLM 自觉遵守，无程序强制
Step2 prompt 写了规则，但代码直接信任 LLM 返回的 overall_result。LLM 可以输出「存在 FAIL 但 overall=ELIGIBLE」而不被拦截。
→ 修复：新增 Final Eligibility Gate：任一 mandatory FAIL → NOT_ELIGIBLE；无 FAIL 但有 INSUFFICIENT → INSUFFICIENT_INFO；全 PASS → ELIGIBLE。程序聚合，LLM 的 overall 仅作参考。

### D4【中】policy_content[:3000] 截断
高企认定管理办法全文 >3000 字，第十一条（核心硬门槛）可能在截断后丢失，导致 Step1 漏召回条件（Hard-Gate Recall 风险）。
→ 修复：提取窗口提高到 6000 字，并优先注入含「条件/门槛/比例/不低于」关键词的段落。

### D5【中】temperature=0.1 非 0
Benchmark 口径要求 temperature=0。
→ 修复：引擎默认 temperature 0。

### D6【中】fallback_evaluation 逻辑死代码：`fails = 0` 永远为 0
LLM 失败时的 fallback 永远不会输出 NOT_ELIGIBLE（只会 ELIGIBLE/INSUFFICIENT_INFO）→ 静默 OVER_LENIENT 通道。
→ 修复：fallback 保守化：无法判定一律 INSUFFICIENT，绝不输出 PASS。

### D7【中】无 Enterprise Fact Normalization
画像字段名与政策字段（employee_count / revenue / rd_ratio）之间无标准映射，LLM 每次自行对齐，表达差异导致 INSUFFICIENT 误判（V1 中 DeepSeek 的 OVER_STRICT 主要根因之一）。
→ 修复：新增 fact normalization 层，输出标准事实表（founded_date、employee_count、tech_staff、rd_expense、revenue、ip_count、has_ip、细分年限等），供 deterministic evaluator 使用。

### D8【中】条件提取未结构化（field/operator/value）
Step1 只输出自然语言 criterion + quote，无法程序化判定，也无法支持条件拆分（“从业人员≤500人、收入≤2亿、资产≤2亿”应拆 3 条）。
→ 修复：Step1 输出增加结构化字段；对数字型条件做正则兜底解析。

### D9【低】API 无 Feature Flag 校验证据（POLICY_ENGINE_V2）
路由未见 feature flag 检查（用户描述中提到）。审计记录，不在本轮修复范围（不影响引擎质量）。

### D10【低】无 token 用量 telemetry
LLMResponse 是否带 usage 需确认；若无，资源成本表按 NOT_AVAILABLE 记录，不编造。

## 2. 可以 deterministic 化的判断（本轮实现范围）
数字比较（>=/<=/>/</=/between）、比例与分档、成立年限（日期差）、人数、收入/资产规模、布尔（有无 IP/高企资质）、枚举（地域/行业 in）。
不适合程序化：语义条件（“对主要产品发挥核心支持作用”）、综合评价分——保留给 LLM，但必须带 evidence_quote。

## 3. INSUFFICIENT 使用准则（写入 V2.1 引擎）
仅当标准事实表中对应字段缺失且该条件为 mandatory 时输出 INSUFFICIENT；画像字段存在但表述不同（如“员工约80人”）由 normalization 层归一，不得因措辞差异输出 INSUFFICIENT；禁止猜测缺失数据。

## 4. Prompt 风险
- OVER_STRICT 风险：Step2 prompt 未告知「画像中已给出的数据可直接使用，不必要求政策原文级别的字段名一致」。
- OVER_LENIENT 风险：Step2 prompt 未禁止使用外部知识补充门槛（V1 已证实混入外部知识是主要幻觉源）。
→ 两条均写入 V2.1 prompt。

## 5. 结论
V2 骨架正确（结构化输出/证据引用/三分类/Evidence Gate 意图齐全），但「数学全靠 LLM + 聚合靠 LLM 自觉 + Gate 误伤企业事实」三点使其当前不具备相对裸 DeepSeek 的可证优势。V2.1 修复以 deterministic evaluator + Final Eligibility Gate + Evidence Gate 精准化为核心。
