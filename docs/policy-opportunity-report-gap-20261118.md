# 政策机会文档交付 · 差距映射（2026-11-18）

目标：客户企业资料 + 政策库 → 可引用机会文档 → 订单权益 → 固定版本下载。

## 管线状态

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 企业建档 / 画像版本钉死 | 已交付 | PolicyScan.profile_version_id |
| 扫描匹配 → Opportunity | 已交付 | matcher + uq_opportunity_scan_policy |
| 资格 + verified Evidence（DB） | 已交付 | evaluate_opportunity + _verify |
| 每机会结构化 gaps / next_step | 本轮补齐（代码） | ReportCard → Deliverable.content_json |
| PDF 硬事实来自结构化卡片 | 本轮补齐（代码） | 去掉「待系统判断」与静态材料章充数 |
| 订单 → 权益 → 冻结 PDF 下载 | 已交付 | 有 frozen / 跨租户测试 |
| LLM 写入付费 PDF 正文 | 不需要（当前） | 付费路径无 LLM；预览 ai_summary 未入交付 |
| 引用忠实度 / 报告质量 eval 门禁 | 本轮补齐 | `citation_fidelity_metrics` + `evals/datasets/report_citation_eval`；下单/付款走 `assert_sellable_report_in_db`（逐字 span） |
| 隔离注册→扫描→购买→下载 | 本轮验过 | 隔离库 `yance_report_loop_test`：`test_policy_report_delivery_loop` 绿 |
| 政策原文覆盖率 | 外部阻塞 | 无规则/无 quote → 大量 NEED_MORE_INFORMATION（采集未混提） |

## P0 阻断「客户拿到可信文档」的项

1. ~~交付 JSON 无 per-opportunity 卡片~~ → `report-card-v1`
2. ~~PDF 用占位/静态清单充数~~ → 卡片驱动
3. ~~内容质量评测门禁与隔离购买→下载~~ → P0-3/P0-4 已绿
4. 数据覆盖：大量机会仍会证据不足（采集/规则，不在本轮混提）；本轮仅让 MISSING 事实仍保留已核验规则原文引用

## 本轮改动文件

- `yance-ai/app/services/report/schema.py` / `quality.py`（新）
- `yance-ai/app/services/agents/policy_scan.py` / `report/pdf.py`
- `yance-ai/app/api/routes/commerce.py` / `services/commerce/delivery.py`
- `yance-ai/app/services/policies/eligibility.py`（MISSING 保留 verified quote）
- `yance-ai/evals/datasets/report_citation_eval/`
- `yance-ai/tests/test_report_*` / `test_policy_report_delivery_loop.py` / `test_eligibility_missing_keeps_quote.py`

未触碰：Ask / 政策采集未提交脏文件、生产开关、价格。
