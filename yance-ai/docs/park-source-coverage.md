# 园区与政策来源覆盖

生成口径：`config/policy_sources/*.yaml` + `config/parks/*.yaml` 实际加载结果（2026-11-06）。所有数字可用 `python -m app.cli policy-collection catalog-summary` 复现。

**六种状态严格区分，不得混用**：已登记 → 已连通 → 已采到原文 → 已解析 → 已进入可用检索 → 已生产运行。

---

## 1. 总体状态（当前真实值）

| 状态 | 数量 | 依据 |
| --- | --- | --- |
| 已登记 | 108 来源 / 31 园区 | YAML 加载成功 |
| 已连通（列表页可访问且解析出条目） | 85 / 90 启用来源 | `harvest_dry_run.py` 全量干跑实测 |
| 已采到原文 | **84 文件 / 3.1MB**（新系统） | `crawler_output/dry_run/` 实存 |
| 旧系统已抽取记录 | 72 条，仅上海 56 / 浙江 16 | `crawler_output/policies.jsonl`，见第 1.2 节 |
| 已解析 | **79 来源 / 85 篇取 79 篇**，另 5 篇正文过短、1 篇抓取失败 | `extract_document_page` 实测，见第 1.1 节 |
| 已进入可用检索 | 0 | 同上 |
| 已生产运行 | **0** | 未部署 |

### 1.1 真实语料解析实测（非合成样本）

全量干跑命令（无 DB、无模型，只读抓取）：

```bash
python scripts/policy_collection/harvest_dry_run.py --level national   --docs 1 --out /tmp/h_nat.json
python scripts/policy_collection/harvest_dry_run.py --level provincial --docs 1 --out /tmp/h_prov.json
python scripts/policy_collection/harvest_dry_run.py --level municipal  --docs 1 --out /tmp/h_city.json
```

| 指标 | 实测值 |
| --- | --- |
| 发起来源 / 启用来源 | 90 / 90（全覆盖） |
| 列表页可访问且有条目 | 85（另 2 源列表失败、3 源列表 0 条） |
| 落盘 HTML | 84 文件 / 3.1MB（`crawler_output/dry_run/`） |
| 正文解析成功（≥200 字） | **79 / 85** |
| 正文过短 | 5 |
| 解析出发布日期 | 62 / 85 |
| 解析出文号 | 26 / 85 |
| 含附件链接 | 23 / 85 |

早期含附件的样本批次（`python scripts/park_policy/parse_dry_run.py --show 4`）：30 = 17 html + 13 附件（7 pdf / 3 ofd / 2 doc / 1 docx），解析 17 篇，仅留存未解析的附件 13 个。

按早期样本批次的来源分布：

| 来源 | 层级 | 已解析 | 仅附件 |
| --- | --- | --- | --- |
| nat_gov_policy | 国家（国务院） | 3 | 0 |
| nat_most_policy | 国家（科技部） | 3 | 4 |
| nat_most_gfxwj | 国家（科技部规范性文件） | 3 | 2 |
| nat_ndrc_tz | 国家（发改委投资） | 2 | 4 |
| nat_ndrc_gfxwj | 国家（发改委规范性文件） | 2 | 2 |
| prov_zhejiang_kjt | 省级（浙江科技厅） | 2 | 0 |
| city_suzhou_kjj | 市级（苏州科技局） | 2 | 1 |

**覆盖了国家、省、市三个层级**，满足阶段 C 的最低代表性要求。

真实样本（原文保留在 `crawler_output/`）：

- `国函〔2026〕113号` 国务院关于辽宁等 9 省区国家级自然保护区…批复，发布日期 2026-11-05，正文 2364 字
- `国办发明电〔2026〕10号` 国务院办公厅关于 2027 年部分节假日安排的通知，2026-11-05，2127 字
- 苏州市 2026 年度第二批创新创业领军人才计划拟立项名单公示，2026-10-30，595 字，含 1 个附件

**口径说明**：`已解析` 指从存下来的字节中提取出标题/正文/日期，**不等于已入库、已进入检索**。PDF/DOCX/OFD 未做确定性解析，因此不计入已解析——这是保守口径，避免把"存下来了"说成"能用了"。

### 1.2 旧采集器遗留数据（务必与上表分开看）

`crawler_output/policies.jsonl` 有 72 条记录，来自旧 `crawler.py`（`crawler_version=policy-crawler-v1`，抓取时间 2026-10-14）。实测分布：

| 维度 | 分布 |
| --- | --- |
| 来源 | `sh_stcsm_xmsb` 19、`sh_stcsm_kjzc` 19、`sh_stcsm_tzgs` 18、`zj_kjt_kjdt` 9、`zj_kjt_tzgg` 7 |
| 层级 | provincial 72（**无国家、无市级**） |
| 省份 | 上海市 56、浙江省 16 |
| 发布日期齐全 | 72 / 72 |
| 正文 > 500 字 | 72 / 72 |

**这 72 条不能计入全国覆盖。** 它只覆盖 2 个省级行政区、5 个栏目，全部为省级，没有一条国家政策，没有任何重点城市市级政策。上一轮"来源主要为上海和浙江"的判断得到实测确认。

两套口径为什么必须分开：旧记录字段是 `source_key` / `support_amount_hint` / `content_chars`，没有内容哈希、没有版本、没有附件记录、没有 robots 与访问规则字段；新系统 `policy_collection` 才有。把两者相加会得出一个既无法回溯版本、也无法区分附件状态的虚假总数。

> 早期任务摘要中"108 来源、pytest 全过"只说明**登记与代码测试**情况，不代表已采到原文。

---

## 2. 国家级（20 个来源）

覆盖国务院及科技、工信、财政、发改、商务、人社、税务、知识产权等主管部门公开栏目。适配器以通用列表页 + 站点适配结合；`gov.cn` 与部委站点的 robots 在采集前逐站检查，`blocked_by_robots=1` 已单独标记并停用。

---

## 3. 省级（31 个省级行政区全覆盖，53 个来源）

| 省/区 | 来源数 | 状态 |
| --- | --- | --- |
| 北京市 | 2 | document_verified 2 |
| 天津市 | 3 | document_verified 3 |
| 上海市 | 2 | document_verified 2 |
| 重庆市 | 2 | document_verified 2 |
| 河北省 | 2 | document_verified 2 |
| 山西省 | 2 | document_verified 1, needs_site_adapter 1 |
| 内蒙古自治区 | 2 | document_verified 2 |
| 辽宁省 | 2 | document_verified 2 |
| 吉林省 | 2 | document_verified 2 |
| 黑龙江省 | 1 | document_verified 1 |
| 江苏省 | 2 | document_verified 1, list_verified 1 |
| 浙江省 | 2 | document_verified 1, needs_site_adapter 1 |
| 安徽省 | 1 | document_verified 1 |
| 福建省 | 2 | document_verified 2 |
| 江西省 | 1 | list_verified 1 |
| 山东省 | 2 | document_verified 2 |
| 河南省 | 1 | document_verified 1 |
| 湖北省 | 2 | document_verified 2 |
| 湖南省 | 2 | document_verified 2 |
| 广东省 | 2 | document_verified 2 |
| 广西壮族自治区 | 1 | document_verified 1 |
| 海南省 | 1 | unreachable 1 |
| 四川省 | 2 | document_verified 2 |
| 贵州省 | 2 | document_verified 2 |
| 云南省 | 2 | document_verified 2 |
| 西藏自治区 | 1 | unreachable 1 |
| 陕西省 | 1 | document_verified 1 |
| 甘肃省 | 1 | unreachable 1 |
| 青海省 | 1 | document_verified 1 |
| 宁夏回族自治区 | 2 | document_verified 2 |
| 新疆维吾尔自治区 | 2 | document_verified 2 |

省级覆盖结论：31 个省级行政区**均有登记**（53 个来源）。其中 27 个省级行政区至少一个来源本轮实测到正文（`document_verified`），江西为 `list_verified`（列表可取、正文过短）；海南、西藏、甘肃 3 个省级来源实测不可达，列为待接入；山西、浙江各有 1 个来源 `needs_site_adapter`。

---

## 4. 首批重点覆盖城市（30 个）

定义为"**首批重点覆盖城市**"，不宣称存在未经核验的"全国科创前 30 名"官方排名。选择依据为可核验、注明年份的公开资料（WIPO 科技集群排名、各地统计公报、工信部专精特新/高企名单等），记录于 `config/policy_sources/priority_cities.yaml`，每条含 `reasons`、`data_sources`、`year=2025`。

| # | 城市 | 类型 | 市级来源 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | 北京市 | 直辖市 | 0（共用省级） | 省级 2 个：document_verified 2 |
| 2 | 上海市 | 直辖市 | 0（共用省级） | 省级 2 个：document_verified 2 |
| 3 | 深圳市 | 计划单列市 | 2 | document_verified 2 |
| 4 | 广州市 | 副省级 | 2 | document_verified 2 |
| 5 | 杭州市 | 副省级 | 1 | registered 1 |
| 6 | 南京市 | 副省级 | 2 | document_verified 2 |
| 7 | 苏州市 | 地级 | 2 | document_verified 2 |
| 8 | 成都市 | 副省级 | 1 | unreachable 1 |
| 9 | 武汉市 | 副省级 | 2 | document_verified 2 |
| 10 | 西安市 | 副省级 | 1 | unreachable 1 |
| 11 | 合肥市 | 省会 | 1 | unreachable 1 |
| 12 | 天津市 | 直辖市 | 0（共用省级） | 省级 3 个：document_verified 3 |
| 13 | 重庆市 | 直辖市 | 0（共用省级） | 省级 2 个：document_verified 2 |
| 14 | 青岛市 | 计划单列市 | 1 | unreachable 1 |
| 15 | 济南市 | 副省级 | 1 | unreachable 1 |
| 16 | 宁波市 | 计划单列市 | 1 | registered 1 |
| 17 | 无锡市 | 地级 | 1 | unreachable 1 |
| 18 | 长沙市 | 省会 | 2 | document_verified 1, list_verified 1 |
| 19 | 郑州市 | 省会 | 1 | unreachable 1 |
| 20 | 东莞市 | 地级 | 1 | unreachable 1 |
| 21 | 厦门市 | 计划单列市 | 2 | document_verified 2 |
| 22 | 福州市 | 省会 | 1 | unreachable 1 |
| 23 | 南昌市 | 省会 | 2 | list_verified 2 |
| 24 | 沈阳市 | 副省级 | 1 | document_verified 1 |
| 25 | 大连市 | 计划单列市 | 1 | blocked_by_robots 1 |
| 26 | 长春市 | 省会 | 1 | document_verified 1 |
| 27 | 哈尔滨市 | 省会 | 1 | unreachable 1 |
| 28 | 昆明市 | 省会 | 1 | document_verified 1 |
| 29 | 贵阳市 | 省会 | 2 | document_verified 2 |
| 30 | 兰州市 | 省会 | 1 | unreachable 1 |

**市级来源实测**：26 城有市级源（35 个）。按 2026-11-06 全量干跑回写的 `verification_state`：`document_verified` 12 城、`list_verified` 2 城（长沙、南昌）、`registered` 2 城（杭州、宁波）、`unreachable` 11 城、`blocked_by_robots` 1 城（大连）。京沪津渝 4 直辖市按规则共用省级来源，**不计重复**。

**结论**：30 城中政策**市级来源实测可取正文**（`document_verified`）的为 12 城，另有 2 城仅列表可用、2 城未连通、11 城不可达、1 城被 robots 拒绝。其余城市只能依赖省级来源或待接入，不得宣称"30 城已完成覆盖"。

---

## 5. 园区目录（31 条）

| 类型 | 数量 | 核验 |
| --- | --- | --- |
| `national_high_tech_zone` | 30 | registered 25、reachable 1、unreachable 4 |
| `economic_dev_zone` | 1（苏州工业园区，国家级经开区） | reachable 1 |

每城取一个代表性国家高新区。**全部 31 条 `boundary_status = needs_confirmation`**：国家高新区实际范围常为"一区多园"或跨区，未经官方边界核验前不得用于判定企业是否适用园区政策。

省级高新区、科技城/科学城、孵化器等载体**尚未登记**，为已知缺口。

---

## 6. 未接入与阻塞清单

| 类别 | 项 | 处理 |
| --- | --- | --- |
| 省级 unreachable | 海南、西藏、甘肃 | 待换入口或站点适配器 |
| 市级 unreachable | 成都、西安、合肥、青岛、济南、无锡、郑州、东莞、福州、哈尔滨、兰州 | 待重测；多为入口改版或反爬 |
| 市级 registered | 杭州、宁波 | 已登记未连通，需实测 |
| needs_site_adapter | 山西、浙江省级、深圳市级 | 需编写站点适配器 |
| blocked_by_robots | 大连市级（1） | 遵守 robots，保持停用 |
| 园区目录 | 省级高新区、科技城、孵化器 | 未登记 |
| 园区边界 | 31 条全部未核验 | 需官方边界材料 |
| 官方解读/问答 | 未独立建模 | 缺口 |

---

## 7. 复现命令

```bash
cd yance-ai
python -m app.cli policy-collection catalog-summary          # 来源/园区统计
python -m app.cli policy-collection verify-source <source_id> # 单源实测
python -m app.cli park-registry summary                       # 园区目录状态
```

未连通的来源**不进入**采集调度队列；`enabled=false` 的来源在检索层空结果说明中单独归因为"来源未启用/暂停"，不得计为"确无更新"。
