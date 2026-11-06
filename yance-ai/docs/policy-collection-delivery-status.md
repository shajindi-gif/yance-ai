---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: af44a43be3f5d56ec87e76066ae0891d_f876a79ed9b611f1ba6252540064ee0f
    ReservedCode1: toBEIhN7I2zlM2JtxzhlDIlrGLSyYbiM8GWe929AJwY3dbu0RZoabpeho3DPrs/A7BcCXe2QTQt0MX1kPMNReWIOx/GCHH4h3nhCObqm8BbMbHMgfoLH+UUU8/1PBboaVoNfqZ9K5YjGVVRDHtv0ydKHneR86NgMM0F7B9MNmPdyXSBJc6CdkppdDaQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: af44a43be3f5d56ec87e76066ae0891d_f876a79ed9b611f1ba6252540064ee0f
    ReservedCode2: toBEIhN7I2zlM2JtxzhlDIlrGLSyYbiM8GWe929AJwY3dbu0RZoabpeho3DPrs/A7BcCXe2QTQt0MX1kPMNReWIOx/GCHH4h3nhCObqm8BbMbHMgfoLH+UUU8/1PBboaVoNfqZ9K5YjGVVRDHtv0ydKHneR86NgMM0F7B9MNmPdyXSBJc6CdkppdDaQ=
---

# 政策采集 + 园区证据系统 · 交付状态（2026-11-06）

本文是收尾口径：**已经真实完成的、以及明确没做的**。所有数字均可按第 6 节命令复现。

---

## 1. 六状态（当前真值）

| 状态 | 值 | 判定依据 |
| --- | --- | --- |
| 已登记 | 108 来源（启用 90）/ 31 园区 | `cli.py validate` 通过 |
| 已连通（列表可访问且解析出条目） | **85 / 90 启用来源**（88 源列表可访问，其中 3 源列表 0 条） | `harvest_dry_run.py` 全量干跑 |
| 已采到原文 | **84 文件 / 3.1MB** | `crawler_output/dry_run/` 实存 |
| 已解析（正文 ≥200 字） | **79 来源 / 85 篇** | `extract_document_page` |
| 已进入可用检索 | **0** | 本机无 PostgreSQL，迁移未执行 |
| 已生产运行 | **0** | 未部署，`43.128.1.64` 零变更 |

园区侧：31 条（30 国家高新区 + 1 经开区），**边界 confirmed 0 / needs_confirmation 31**，因此园区适用范围判定一律 `needs_review`。这是刻意设计，不是遗漏。

---

## 2. 本轮真正推进的部分

上一轮状态是"已连通 80、采到原文 7 源 30 文件、解析 17 篇"。本轮把采集面从样本级推到全覆盖：

| 项 | 上轮 | 本轮 |
| --- | --- | --- |
| 实发请求的来源 | 7 | **90（全部启用来源）** |
| 能解析出条目 | 80（仅连首页） | **85（列表页真实解析）** |
| 采到并落盘原文 | 30 文件 | **84 文件 / 3.1MB（85 篇抓取，1 篇失败）** |
| 正文解析成功 | 17 篇 | **79 来源 / 79 篇** |
| 目录状态回写 | 无 | **90 个来源块写回真实状态 + 时间戳** |

新增两个可复现脚本：

- `scripts/policy_collection/harvest_dry_run.py`：无 DB、无模型，只读抓列表 + 正文 + 解析，落原始字节。
- `scripts/policy_collection/record_verification.py`：把干跑结果按行写回 `config/policy_sources/*.yaml`，只改 `verification_state` / `last_verified_at` / `notes`，不动注释与其它字段。

`cli.py run` 依赖 PostgreSQL，本机没有库，所以走"干跑 + 回写"这条不碰数据库的路径推进覆盖，避免为了跑通而谎称已入库。

### 2.1 本轮补的解析缺陷：跳转壳被 CMS 脚本"撑胖"

`detect_client_redirect` 原先用**整篇文档**的非空白字符数判断"这是不是一个只有跳转的壳页"（阈值 200 字）。但政府站点的跳转壳往往顺手引入整套 CMS 脚本与样式，脚本源码本身就把字数顶过阈值，于是壳页被当成正文页，`entries=0` 且看起来像"选择器规则失效"。

修法：判断瘦度时先剥掉 `<script>` / `<style>` 再看可见文本，跳转目标仍在全文里匹配。配套新增 `probe_source.py --follow`，可沿跳转链落到真实页面再看能否解析。

实测效果：`prov_jilin_kjt_zcfg`（列表超时→可解析）、`city_shenzhen_stic_zcfg`（0 条→20 条）两个来源恢复；`nat_miit_policy` 与 `prov_zhejiang_kjt_zcfg` 确认是客户端渲染，降级为 `needs_site_adapter`，不再假装是规则问题。全量干跑结果随之从"83 源有条目"升到 **85 源**。

### 2.2 回写脚本的两个 bug（本轮修掉）

1. **重放会刷新时间戳**：`record_verification.py` 原先无条件重写 `last_verified_at`，同一份干跑结果跑两遍，28 个 YAML 全被改动、`last_verified_at` 变成"现在"，看起来像刚复核过。现在先判断状态与备注是否真的变化，无变化整块不动；重放输出 `0 source block(s) touched`。手动写的折行备注（`notes: >-`）视为已记录，不再反复追加。
2. **折行备注块被插坏**：块内已有 `notes: >-` 而缺 `last_verified_at` 时，新插入的行落在 `notes: >-` 与它的缩进正文之间，YAML 直接解析失败（`expected <block end>, but found '<scalar>'`）。新增字段现在插到 `notes` 行之前。

两条都有回归测试：`tests/policy_collection/test_record_verification.py`（3 例，含"重放不重写目录"与"折行块不被追加"）。

---

## 3. 已知缺陷（5 个来源，逐条留证）

| source_id | 实测 | 影响 | 修法 |
| --- | --- | --- | --- |
| `nat_tax_policy` | http 404 | 税务总局政策法规栏目入口已失效 | 需人工重定位现栏目 URL |
| `nat_miit_policy` | JS 跳转壳，跟随后为搜索页（客户端渲染） | 工信部政策文件列表不在静态 HTML 内 | 接官网检索接口或引入浏览器渲染 |
| `prov_shanxi_kjt_sbzt` | 列表 0 条 | 山西申报专题改版 | 需重抓页面结构改选择器 |
| `prov_zhejiang_kjt_zcfg` | JS 跳转壳，跟随后列表仍由脚本加载 | 浙江政策法规（`site_specific`）改版 | 同上 |
| `city_dalian_kjj` | robots.txt 禁止 | 大连科技局禁止抓取 | **按规则不采**，保持登记 |

另 11 个市级来源（东莞、兰州、合肥、哈尔滨、成都、无锡、济南、福州、西安、郑州、青岛）为 `unreachable`：站点直接访问失败，需要换用浏览器方式人工定位正确栏目。

---

## 4. 明确的未完成项

| 项 | 阻塞原因 | 需要什么 |
| --- | --- | --- |
| 入库 / 建索引 / 检索 | 本机无 PostgreSQL，`0036`/`0037` 迁移未在真实 PG 上验证 | 数据库连接串 + 允许建库 |
| 向量化 | 无模型供应商配置 | API Key 与预算上限 |
| 生产部署 | 只做了 SSH 指纹采集，未登录 | **认证方式**（密钥或密码） |
| 定时采集 | 依赖部署 | 同上 |
| 园区边界核验 | 边界数据无官方现成数据集 | 官方边界文件或允许人工逐条确认 |
| A/B 对照评测 | 无模型配置，A/B 臂 blocked | 同"向量化" |

上一轮评测结论仍然成立：**insufficient**，不宣称优于通用模型。

---

## 5. 文档索引

| 文档 | 内容 |
| --- | --- |
| `policy-collection-coverage.md` | 108 来源覆盖矩阵、六状态、逐源实测 |
| `policy-collection-implementation.md` | 缺陷修复对应、模块职责、`duplicate_entry_urls` 口径 |
| `policy-collection-runbook.md` | 运维步骤、资源与费用估算 |
| `policy-collection-test-report.md` | 测试与全量干跑实测数据 |
| `park-source-coverage.md` | 园区与证据层状态 |
| `park-policy-data-strategy.md` | 30 城选择依据与局限 |
| `park-policy-release-runbook.md` | 园区侧发布步骤 |
| `park-workspace-implementation.md` | 园区工作区实现 |
| `policy-evidence-schema.md` | 证据与版本字段口径 |
| `policy-retrieval-evaluation.md` | 检索评测设计与结论 |

---

## 6. 复现命令

```bash
cd /Users/shajindi/yance-backup/yance/yance-ai

# 目录合法性（应输出 validate: OK）
.venv/bin/python scripts/policy_collection/cli.py validate

# 全量干跑（无 DB、无模型；约 5–8 分钟）
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level national   --docs 1 --out crawler_output/dry_run/harvest_national.json
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level provincial --docs 1 --out crawler_output/dry_run/harvest_provincial.json
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level municipal  --docs 1 --out crawler_output/dry_run/harvest_municipal.json

# 回写目录状态（先加 --dry-run 复核；跑前备份 config/policy_sources/）
.venv/bin/python scripts/policy_collection/record_verification.py \
  --from crawler_output/dry_run/harvest_national.json \
  --from crawler_output/dry_run/harvest_provincial.json \
  --from crawler_output/dry_run/harvest_municipal.json --dry-run

# 同一份干跑结果重放应输出 "0 source block(s) touched"（幂等，不会刷新时间戳）

# 园区目录
.venv/bin/python scripts/park_policy/cli.py parks summary

# 不依赖 DB 的测试（129 passed）
.venv/bin/python -m pytest tests/policy_collection tests/park_policy -q
```

全量 `pytest tests` 的失败项均为需要 PostgreSQL 的既有 `test_v2_*` 等用例，与本轮改动无关。
*（内容由AI生成，仅供参考）*
