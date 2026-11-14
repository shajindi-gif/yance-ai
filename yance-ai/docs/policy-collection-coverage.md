# 全国政策采集 · 覆盖矩阵

本文回答一个问题：**108 个登记来源里，真正能用的是哪些。** 所有数字可用文末命令复现。

园区/证据层见 `park-source-coverage.md`；采集实现见 `policy-collection-implementation.md`。

---

## 1. 六状态总表（2026-11-06 全量干跑实测）

本轮对 **90 个启用来源全部发起真实请求**（1 次列表页 + 每源 1 篇正文），结果写回目录 `verification_state`。

| 状态 | 数量 | 判定依据 |
| --- | --- | --- |
| 已登记 | **108 来源**（启用 90） | `policy_collection/cli.py validate` 通过 |
| 已连通（列表页可访问且解析出条目） | **85 / 90 启用来源** | `harvest_dry_run.py` 实测：88 源列表可访问，其中 3 源列表 0 条；另 2 源列表失败 |
| 已采到原文 | **84 文件 / 3.1MB** | `crawler_output/dry_run/` 实存（85 篇抓取，1 篇失败未落盘） |
| 已解析（正文 ≥200 字） | **79 来源 / 85 篇取 79 篇** | `extract_document_page` 实测（另 5 篇正文过短、1 篇抓取失败） |
| 已进入可用检索 | **0** | 无 DB，迁移未执行 |
| 已生产运行 | **0** | 未部署，服务器只读核查未完成 |

目录状态分布（108 源）：`document_verified` 79、`list_verified` 6、`unreachable` 16、`needs_site_adapter` 3、`registered` 3、`blocked_by_robots` 1。

干跑失败/空列表明细（5 源）：

| source_id | 实测结果 | 处置 |
| --- | --- | --- |
| `nat_tax_policy` | http 404 | 入口栏目已失效，标记 unreachable，待重定位 |
| `city_dalian_kjj` | robots.txt 禁止 | 按规则不采，标记 blocked_by_robots |
| `nat_miit_policy` | 入口是 JS 跳转壳，跟随后为搜索页，仍须客户端渲染才能取列表 | 标记 needs_site_adapter，待接官方检索接口 |
| `prov_shanxi_kjt_sbzt` | 列表 0 条 | 标记 needs_site_adapter |
| `prov_zhejiang_kjt_zcfg` | 入口是 JS 跳转壳，跟随后列表仍由脚本加载 | 标记 needs_site_adapter |

`prov_jilin_kjt_zcfg` 与 `city_shenzhen_stic_zcfg` 在本轮复测中已恢复（跳转壳跟随修复后列表页能解析出条目），因此不再列为失败源。

**"已登记"不等于"已覆盖"，"采到原文"也不等于"已入库可检索"。** 本轮只推进到"能在真实站点上抓到并解析出正文"，没有一条进入数据库，因此检索侧仍为 0。

---

## 2. 国家级（20 个来源，启用 18）

覆盖国务院、科技部、工信部、财政部、发改委、商务部、人社部、税务总局、知识产权局等主管部门公开栏目。

| 状态 | 数量 | 来源 |
| --- | --- | --- |
| document_verified（已采到并解析原文） | **15** | 国务院、科技部、发改委、财政部、商务部、知识产权局等主力栏目 |
| list_verified（列表可解析、正文过短或需附件解析） | 1 | `nat_cnipa_notice`（157 字，正文在附件里） |
| unreachable | 2 | `nat_tax_policy`（实测 404）、`nat_mohrss`（未启用） |
| needs_site_adapter | 1 | `nat_miit_policy`（入口是 JS 跳转壳，跟随后为搜索页，需客户端渲染，待接官方检索接口） |
| registered | 1 | 未启用来源 |

国家级实测抓到的正文样本含 2026-11-05 国务院令与国办发明电，文号解析正常（`国函〔2026〕113号`、`国办发明电〔2026〕10号`）。

---

## 3. 省级（31 个省级行政区，53 个来源，启用 50）

31 个省级行政区全部有登记，**22 个省全部来源达 document_verified**，另有 5 个省仅部分来源达标。

| 状态 | 数量 | 说明 |
| --- | --- | --- |
| document_verified | **46** | 覆盖 22 个省份全部来源 |
| list_verified | 2 | 江苏 `prov_jiangsu_kxjst`、江西 `prov_jiangxi_kjt`（列表可取，正文过短） |
| needs_site_adapter | 2 | 山西 `prov_shanxi_kjt_sbzt`（列表 0 条）、浙江 `prov_zhejiang_kjt_zcfg`（JS 跳转壳，跟随后仍需脚本渲染） |
| unreachable | 3 | 海南、甘肃、西藏（站点不可访问） |

未达标省份共 7 个：山西、江苏、江西、浙江（各有 1 个来源待修）、海南、甘肃、西藏（整省不可访问）。吉林 `prov_jilin_kjt_zcfg` 本轮复测已恢复（跳转壳跟随修复后列表可解析），不再是缺口。

**口径**：省级政策的适用范围是全省，不限定省会。已在 `geography.py` 中通过 `scope_type=province` 仅比较 province 字段保证；实测企业填江苏省徐州市（非省会）仍判 `satisfied`。

---

## 4. 重点 30 城（35 个市级来源，启用 22）

| 状态 | 数量 | 说明 |
| --- | --- | --- |
| document_verified | **18** | 苏州、深圳、广州、南京、武汉、厦门、沈阳、昆明、贵阳、长春等 |
| list_verified | 3 | 长沙、南昌（2 个栏目） |
| blocked_by_robots | 1 | 大连（`robots.txt` 禁止，按规则不采） |
| registered | 2 | 杭州、宁波（未启用） |
| unreachable | 11 | 东莞、兰州、合肥、哈尔滨、成都、无锡、济南、福州、西安、郑州、青岛 |

26 个已建目录城市中，**9 城全部来源达 document_verified**（另有 3 城部分来源达标）；11 城站点不可访问是当前最大缺口，需要用浏览器方式人工定位正确栏目后重建入口。

30 城选择依据与局限见 `park-policy-data-strategy.md`。这里只强调：**没有"全国科创前 30 名"的官方排名**，这是我们自选的首批重点覆盖城市，不宣称官方性。

---

## 5. 旧采集器遗留数据（不得计入上表）

`crawler_output/policies.jsonl` 72 条，`crawler_version=policy-crawler-v1`，抓取于 2026-10-14。

| 维度 | 实测分布 |
| --- | --- |
| 来源 | sh_stcsm_xmsb 19 / sh_stcsm_kjzc 19 / sh_stcsm_tzgs 18 / zj_kjt_kjdt 9 / zj_kjt_tzgg 7 |
| 层级 | 全部 provincial（无国家、无市级） |
| 省市 | 上海市 56 / 浙江省 16 |
| 发布日期 | 72/72 齐全 |

这正是上一轮"来源主要为上海和浙江，不能代表全国覆盖"的实测确认。旧记录缺内容哈希、版本、附件、robots 字段，与新系统不可相加。

---

## 6. 园区目录（本轮新增）

31 条：30 个国家高新区 + 1 个经开区。

| 维度 | 分布 |
| --- | --- |
| 类型 | national_high_tech_zone 30、economic_dev_zone 1 |
| 核验 | registered 25、reachable 2、unreachable 4 |
| 边界 | **needs_confirmation 31（confirmed 0）** |

边界全部未核验的直接后果：所有园区政策的地理适用范围一律返回 `needs_review`，系统不会因为企业地址在园区内就判"符合"。这是刻意设计。

省级高新区、科技城、孵化器尚未纳入，待官方名录。

---

## 7. 复现命令

```bash
cd /Users/shajindi/yance-backup/yance/yance-ai

.venv/bin/python scripts/policy_collection/cli.py validate
.venv/bin/python scripts/policy_collection/cli.py plan --limit 200
.venv/bin/python scripts/policy_collection/cli.py verify --level provincial
.venv/bin/python scripts/policy_collection/cli.py coverage --markdown
.venv/bin/python scripts/park_policy/cli.py parks summary
.venv/bin/python scripts/park_policy/parse_dry_run.py --show 4

# 本文第 1 节六状态的复现（无 DB、无模型，只读抓取）
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level national --docs 1 --out /tmp/h_nat.json
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level provincial --docs 1 --out /tmp/h_prov.json
.venv/bin/python scripts/policy_collection/harvest_dry_run.py --level municipal --docs 1 --out /tmp/h_city.json
.venv/bin/python scripts/policy_collection/record_verification.py \
  --from /tmp/h_nat.json --from /tmp/h_prov.json --from /tmp/h_city.json --dry-run

# 遗留数据分布
.venv/bin/python -c "
import json,collections
rows=[json.loads(l) for l in open('crawler_output/policies.jsonl')]
print(dict(collections.Counter(r['province'] for r in rows)))"
```

`coverage --markdown` 需要 DB；无 DB 时返回退出码 3 并提示可用替代命令。`record_verification.py` 会改写目录 YAML 的状态字段，跑前先备份 `config/policy_sources/`。
