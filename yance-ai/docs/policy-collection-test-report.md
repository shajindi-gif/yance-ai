# 全国政策采集 · 测试报告

执行环境：macOS 27.2 / Python 3.12 / 仓库 `/Users/shajindi/yance-backup/yance` 分支 `feature/investor-grade-upgrade`（提交 `0c35d70`，全部改动未提交）

## 0. 一句话结论

**130 个用例通过（无 DB 依赖部分全绿），需要 PostgreSQL 的集成与端到端场景未执行。** 不得据此宣称系统已验证可用。

---

## 1. 已执行

```bash
cd yance-ai
.venv/bin/python -m pytest tests/park_policy tests/policy_collection -p no:cacheprovider
# => 130 passed, 5 warnings in 1.82s
```

| 测试文件 | 用例 | 覆盖 |
| --- | --- | --- |
| `tests/policy_collection/test_collection_pipeline.py` | 36 | URL 守卫、robots、抓取限额、增量判定、幂等、窗口、质量门、跳转壳识别 |
| `tests/policy_collection/test_record_verification.py` | 4 | 目录回写：只改 3 个字段、重放幂等、失败类型不误标、瞬时超时不落笔 |
| `tests/park_policy/test_conditions_evidence.py` | 24 | 条件矩阵、证据约束、金额与期间、冲突事实 |
| `tests/park_policy/test_park_catalog_geography.py` | 15 | 园区目录、地域判定、地址不等于资格 |
| `tests/park_policy/test_park_retrieval.py` | 15 | 混合检索、权限过滤、别名 |
| `tests/park_policy/test_evaluation.py` | 13 | 评测集校验、家族隔离、A/B 阻塞、总分拒绝 |
| `tests/policy_collection/test_runner_integration.py` | 12 | 单源全链路、附件失败、零新增归因 |
| `tests/park_policy/test_real_corpus_parse.py` | 6 | **真实采集语料解析**（非合成） |
| `tests/policy_collection/test_open_api_adapter.py` | 5 | 开放接口适配器 |

---

## 2. 逐条对照发布门槛

| 门槛项 | 用例 | 结果 |
| --- | --- | --- |
| 相同任务重跑不重复入库 | `test_rerun_is_idempotent_and_reports_zero_new`、`test_rerun_same_document_is_idempotent` | 通过 |
| 相同 URL 更新保留旧证据并生成新版本 | `test_same_url_new_content_creates_version_and_keeps_old` | 通过 |
| 转载不被错误合并 | `test_repost_from_other_source_is_linked_not_merged` | 通过 |
| 不同批次/年度不合并 | `test_batches_are_not_merged_across_years`、`test_distinct_application_rounds_are_not_merged` | 通过 |
| 省级范围不误缩省会 | `test_provincial_scope_is_not_narrowed_to_capital` | 通过 |
| 错误日期（导航日期/未来日期） | `test_list_navigation_dates_are_not_taken_as_publish_dates`、`test_implausible_publish_date_is_rejected` | 通过 |
| 缺失金额保持未知 | `test_missing_amount_stays_unknown`、`test_amount_ceiling_is_not_reported_as_entitlement` | 通过 |
| 过期/延期/撤回/冲突 | `test_expired_policy`、`test_expired_and_extended_notices_are_classified_differently`、`test_repeal_document_wins`、`test_source_anomaly_does_not_repeal_policy` | 通过 |
| robots 限制 | `test_robots_disallow_blocks_request`、`test_robots_disallow_yields_blocked_outcome`、`test_robots_allow_path` | 通过 |
| 429 | `test_429_is_retried_then_reported` | 通过 |
| 超时 | `test_timeout_is_reported_not_raised` | 通过 |
| 异常重定向 / 内网 / 云元数据 | `test_redirect_to_internal_address_is_blocked`、`test_cloud_metadata_endpoint_is_blocked` | 通过 |
| 超大响应 / 超大附件 | `test_oversized_response_is_rejected`、`test_oversized_article_is_rejected_without_ingestion` | 通过 |
| 分页预算 | `test_pagination_budget_respects_source_max_pages` | 通过 |
| 附件失败不静默 | `test_attachment_failure_is_recorded_not_silently_ignored`、`test_unsupported_attachment_is_marked_unsupported_not_parsed` | 通过 |
| 模型不可用不伪造 | `test_configured_api_missing_key_fails_loudly`、`test_model_arms_are_blocked_not_simulated` | 通过 |
| 客户私有资料不混入公开库 | `test_public_policy_payloads_carry_no_tenant_id`、`test_tenant_is_mandatory_and_fails_closed`、`test_memory_store_has_no_tenant_dimension` | 通过 |
| 停用采集不影响读取 | `test_paused_source_is_not_collected_but_policies_stay_readable` | 通过 |
| 园区地址不等于资格 | `test_address_only_snapshot_cannot_grant_park_membership`、`test_unconfirmed_boundary_blocks_park_scope` | 通过 |

---

## 3. 未执行（明确标注，不得视为通过）

| 项 | 原因 | 需要什么 |
| --- | --- | --- |
| 任务锁并发、stale lock 回收 | 需 DB 行锁 | PostgreSQL |
| 断点续跑 / 服务器重启恢复 | 需 DB + 真实调度 | PostgreSQL + 部署 |
| 备份恢复 | 需 DB | PostgreSQL |
| 迁移 upgrade/downgrade 双向往返 | 本机无 DB | PostgreSQL |
| 新旧应用数据库兼容 | 同上 | 迁移后回跑旧版测试 |
| 真实分页中断（第 2 页 500） | 需可控站点 | 真实站点或半隔离测试服 |
| PDF/DOCX/OFD 确定性解析 | 未接入解析库 | 依赖安装 + 授权 |
| 向量化与检索 Recall@K | 无 DB、无模型预算 | 见 `policy-retrieval-evaluation.md` |
| 浏览器渲染适配器 | 未实现 | 站点需要时才做 |

**全量 `pytest` 的失败项**：需要 PostgreSQL 的既有测试（`test_v2_*`、`test_funding_os`、`test_investor_demo`、`test_order_retry` 等）报 `OperationalError`，原因是本机无数据库，与本轮改动文件无关。这些失败在改动前同样存在——本轮新增文件均为独立模块，未改动其导入路径。

---

## 4. 真实语料解析实测

### 4.1 全量干跑（90 个启用来源，2026-11-06）

```bash
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level national   --docs 1 --out /tmp/h_nat.json
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level provincial --docs 1 --out /tmp/h_prov.json
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level municipal  --docs 1 --out /tmp/h_city.json
```

| 指标 | 国家级 | 省级 | 市级 | 合计 |
| --- | --- | --- | --- | --- |
| 发起来源 | 18 | 50 | 22 | **90** |
| 列表页可访问且有条目 | 17 | 50 | 21 | **88**（其中 3 源列表 0 条，实际有条目 85） |
| 抓取正文 | 16 | 48 | 21 | **85** |
| 正文解析成功（≥200 字） | 15 | 46 | 18 | **79** |
| 正文过短 | 1 | 1 | 3 | 5 |
| 取到发布日期 | 16 | 34 | 12 | **62** |
| 取到文号 | 7 | 15 | 4 | **26** |
| 含附件链接 | 6 | 11 | 6 | **23** |

落盘证据：`crawler_output/dry_run/` 共 85 个 HTML，3.1MB。列表页失败 3 源（404 / 超时 / robots），空列表 4 源，明细见 `policy-collection-coverage.md` 第 1 节。

### 4.2 早期样本批次

```bash
.venv/bin/python scripts/park_policy/parse_dry_run.py --show 4
```

| 指标 | 值 |
| --- | --- |
| 文件 | 30 = 17 html + 13 附件 |
| 已解析 | 17 |
| 有发布日期 | 15 |
| 有文号 | 7 |
| 有附件链接 | 8 |
| 正文过短（判失败） | 0 |

来源覆盖国家（国务院、科技部、发改委）、省（浙江科技厅）、市（苏州科技局）三层。样本如 `国函〔2026〕113号`（2026-11-05，2364 字）。

这不是合成样本：字节来自真实站点抓取，存于 `crawler_output/policy_raw/` 与 `crawler_output/dry_run/`。

---

## 5. 评测运行

```bash
.venv/bin/python scripts/park_policy/cli.py eval run --out docs/evidence/eval-report-2026-11-06.json
```

| 臂 | 状态 | 结果 |
| --- | --- | --- |
| A 通用模型 | blocked | 无供应商配置与预算 |
| B 同模型+语料 | blocked | 同上 |
| C 衍策规则核心 | runnable | 21 题 behavior_match 1.0、severe 0、invented 0 |
| 过度声明基线 | runnable | behavior_match 0.4286、**severe 0.5714**、invented **21/21** |

业务质量结论：`insufficient`。工程类通过率不得用于证明业务准确率。

---

## 6. 复现

```bash
cd /Users/shajindi/yance-backup/yance/yance-ai
.venv/bin/python -m pytest tests/park_policy tests/policy_collection -p no:cacheprovider
.venv/bin/python scripts/park_policy/cli.py parks validate
.venv/bin/python scripts/park_policy/parse_dry_run.py
.venv/bin/python scripts/park_policy/cli.py eval run --out /tmp/eval.json
```
