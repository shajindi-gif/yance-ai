# 全链路（采集→结构化→匹配→交付）2026-11-18

生产热补丁：`opportunity-20261118-03e` · Ask=`false` · 合成无真扣款

## A. 采集入口（本客户端可操作）

| 入口 | 路径/命令 |
|---|---|
| 代码栈（=Marvis） | `yance-ai/app/services/policy_collection/` |
| CLI | `scripts/policy_collection/cli.py` |
| 源目录 | `config/policy_sources/{national,provincial,municipal,priority_cities}.yaml`（prod 约 108 sources） |
| 生产开关 | `POLICY_COLLECTION_ENABLED=false`（调度关）；**manual `trigger=manual` 仍可跑** |
| 执行形态 | docker api 容器内 `execute_source_run` / `backfill.run_batch(BackfillConfig, source_ids=...)` |

### 本轮采集相对饱和首屏

- 沪科委 / 粤科技厅 / 科技部 / 发改等：多为 `unchanged`
- 科技部规范性文件：**+1 new**；工信部最新政策：**7 updated**；广州科技：**1 updated**
- 深圳 stic：Cloudflare/403，源已 pause（不伪造）

### 库覆盖（yance_prod 现况）

- published policies **1405**
- versions **2398**（正文 length>50：**2397**）
- 任一日期字段非空：**105** / 2398（密度仍低）
- active hard rules **369** · 有规则 version **227**

## B. 结构化

- 规则补种：沪/粤/全国主题已饱和（created≈0）
- 日期：可核实才回填；拒绝 expires&lt;effective；错误样例已回滚
- exact-span hard gate 仍要求 version+chunk quote

## C/E. 三切片合成验收（`/tmp/run_three_full.sh` → 全 pass）

| 切片 | pass | 缺规则 | 正例 verified | NEED_MORE | SHA=frozen | PDF |
|---|---|---:|---:|---:|---|---|
| 上海+AI | true | 13.6% | 28 | 16 | true | 534204 B |
| 广东+制造 | true | 13.6% | 35 | 9 | true | 522638 B |
| 全国软件(province空) | true | 10.0% | 8 | 2 | true | 455549 B |

硬错配：三切片均为 **0**。

## 样例与截图（本机）

- PDF：`yance-ai/docs/releases/sample_pdfs/sample_{shanghai_ai,guangdong_mfg,national_soft}.pdf`
- 截图桌面/手机：`yance-ai/docs/releases/pdf_shots/{sh,gd}_{desk,mobile}.png` + `sh_p3.png`（总览/Top）
- 生产 `/tmp` 同名样例仍保留

封面：品牌 + 报告名 + 审计元数据；非噪声名单首屏。  
一策一卡：正例有 `原文依据` 逐字 span；NEED_MORE 带版本/画像/原文区间引用（非空壳劝退）。

## 网页切换（已执行候选 1）

- 保持 API `opportunity-20261118-03e` + 网页 `website-20261118-02`（未全量重建前端、Ask 仍 false）
- `release.json` 已标 `api_application_version=opportunity-20261118-03e`
- 样例入口：`/samples/index.html`（三份合成 PDF + 桌面/手机截图）
- 候选 2（整站切到 design 分支）**未做**，避免混入未提交 Ask/collector 脏改动

## 仍劝退 / 下一刀

- 采集首屏饱和；深页/附件/区县未扩；深圳源站故障
- 日期字段密度低 → 卡片大量「截止日未收录」专业缺口文案（诚实但观感偏「材料不齐」）
- Top 排序仍可能把全国泛政策（会计改革/宣传月）顶到 100%——有用性门禁下一刀应加强「同城/同业/补贴窗口」升权与活动类降权
- 行业硬规则需适用对象句式精确抽取后再启用（当前禁噪声 industry hard-gate）
