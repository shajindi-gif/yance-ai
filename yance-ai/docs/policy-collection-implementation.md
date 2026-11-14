# 全国政策采集 · 实现说明

代码位置：`yance-ai/app/services/policy_collection/`、`yance-ai/scripts/policy_collection/`
来源配置：`yance-ai/config/policy_sources/{national,provincial,municipal,priority_cities}.yaml`
模型与表：`app/models/policy_collection.py`，迁移 `alembic/versions/20261106_0036_policy_collection.py`

本轮**未新建任何平行采集系统**。旧 `scripts/policy_crawler/crawler.py` 保留为参考，新链路在它之上修正了下列五个已知缺陷。

---

## 1. 上一轮遗留缺陷与修复对应

| 遗留线索 | 实测结论 | 处理 |
| --- | --- | --- |
| 来源主要为上海和浙江 | **确认**。旧 `policies.jsonl` 72 条＝上海 56 + 浙江 16，全为省级 | 新目录扩至 108 来源，覆盖国家 20 / 省 53 / 市 35 |
| 相同 `source_url` 直接跳过，漏掉原文更新 | **确认**。旧逻辑无内容哈希 | `fingerprint.decide_change` 输出 `new_version` / `repost_new_source` / `repost_updated`，同 URL 内容变化生成新版本并保留旧版 |
| 注释称遵守 robots 但未实现 | **确认**（旧代码无解析） | `robots.py` 真解析 `User-agent` / `Disallow` / `Crawl-delay`，`blocked_by_robots` 为一等状态 |
| 附件处理 | 未实现 | `rawstore.RawEvidenceStore` 按 `source_id/sha256` 前缀落盘，附件独立记录 |
| 省级范围误缩为省会 | 存在风险 | `jurisdiction_for()` + `scope_type=province` 仅比 province |
| 地域字段字符串裁剪 | 不可靠 | 改为配置显式声明 province/city，不做 `title.split()` |
| 分页/发布日期取导航日期 | 有风险 | `parse_cn_date` + `_date_from_labels` 只认 `pubdate` 类 meta 或正文标签，实测 85 篇中 62 篇取到日期（国家级 16/16、省级 34/48、市级 12/21，日期多挂在正文标签而非列表页） |

---

## 2. 模块职责

| 模块 | 职责 | 关键约束 |
| --- | --- | --- |
| `urlguard.py` | 逐跳校验域名、协议、目标 IP | `is_blocked_ip` 阻断内网/环回/云元数据；`resolve_ips` 解析后再校验，防 DNS 重绑定 |
| `robots.py` | robots 解析与缓存 | 按 host 缓存，`Crawl-delay` 参与限速 |
| `fetch.py` | 安全抓取 | `HostRateLimiter` 单站最小间隔；响应字节上限；超时；重试上限；记录 HTTP 元信息 |
| `adapters.py` | 列表适配器 | `GenericListAdapter` / `JpaasListAdapter` / `OpenApiListAdapter`；官方接口与 RSS 优先 |
| `extract.py` | 列表与正文抽取 | 导航日期与政策发布日期分开；`parsed_thin` 判为解析失败 |
| `classify.py` | 支持形式识别 | `detect_support_forms` 区分项目资助/认定/认定奖励/贷款贴息/税收优惠/服务券；无依据不下"现金补贴"结论 |
| `fingerprint.py` | 增量判定 | 五种 `ChangeKind`；`batch_signature` 区分不同年度批次 |
| `rawstore.py` | 原文留存 | 内容寻址，保存最终 URL、机构、抓取时间、HTTP 元信息、文件类型、sha256、解析版本 |
| `store.py` | 幂等入库 | `PolicyStore` 协议，`DocumentPayload` 含窗口与附件 |
| `runner.py` | 单源运行 | `CollectionLimits` 限条数/页数；`zero_reason` 区分规则失效与抓取失败 |
| `service.py` | 任务编排 | DB 行锁保证单源单跑；stale lock 回收；run 记录；健康度；暂停熔断 |
| `catalog.py` | 来源目录 | 加载与校验 YAML；`source_id` 唯一；允许域名非空 |

---

## 3. "新增 0 条"必须可解释

`runner.SourceRunOutcome.zero_reason` 返回四种之一：

| 值 | 含义 | 运维动作 |
| --- | --- | --- |
| `no_change` | 确无更新 | 无需动作 |
| `rule_broken` | 列表规则失效（`empty_list` / `selector_miss`） | 修适配器 |
| `fetch_failed` | 站点失败（网络/超时/robots/阻止） | 检查站点或退避 |
| `paused` | 已暂停 | 按需恢复 |

这条是硬要求：把三种情况都显示成"0 条"等于掩盖故障。

---

## 4. 安全与资源限制

| 限制 | 实现 |
| --- | --- |
| 域名白名单 | 每来源 `allowed_domains`，重定向逐跳校验 |
| SSRF 阻断 | 内网段、环回、链路本地、云元数据地址一律拒绝 |
| 响应体上限 | 页面与附件分别设限，超限截断并记失败 |
| 解压体积 | 附件仅保存不自动解压，避免压缩炸弹 |
| 解析时长 | 单文档超时即放弃，不阻塞整轮 |
| 重试 | 指数退避 + 次数上限，失败留证据 |
| 并发 | 单站串行 + 最小间隔，不冲击站点 |
| 与在线业务隔离 | 采集为独立进程，独立 Worker，不占 API 进程资源 |

不绕过登录、验证码、访问限制。`blocked_by_robots` 的来源保持登记，不采。

### 4.1 关于 `duplicate_entry_urls: 2`

`validate` 报 2 个重复 `entry_url`，均为发改委同一栏目 `https://www.ndrc.gov.cn/xxgk/wjk/` 下的三个来源（`nat_ndrc_wjk` / `nat_ndrc_gfxwj` / `nat_ndrc_tz`）。它们共用页面取 `key`，再用不同 `tab` 参数（`wjk` / `gfxwj` / `tz`）命中不同数据集合，实际采到的文件集合不重叠。这是登记口径导致的重名，不是重复采集，因此不合并；若后续接入按 URL 去重的统计，需要以 `source_id + api.params.tab` 为准。

---

## 5. 增量与版本

```
同 URL + 内容哈希变化      → new_version（旧版保留）
同 URL + 哈希不变          → unchanged（跳过向量化，省费用）
不同 URL + 同文号/同机构   → repost_new_source（建立关联，不抹去来源）
不同 URL + 内容差异        → repost_updated
内容哈希、文号、机构联合   → same_document_key 辅助去重
```

`batch_signature(title)` 提取年度与批次号，把"2025 年第二批"与"2026 年第一批"分成不同申报窗口，不合并成一条截止日期。

404 或抓取失败**不**自动判为废止：保留旧证据，标异常，等待人工或再次验证。

---

## 6. 未实现（明确缺口）

1. **PDF/DOCX/OFD 确定性解析未接入**：13 个附件仅留存。扫描件 OCR 未接，需标注可信度
2. **向量化未运行**：无 DB、无模型预算
3. **外发告警未接**：仅本地日志与 `status` 命令
4. **字段级原文位置**：`classify.py` 返回句子级证据，但未做字符偏移回填到 `policy_chunks`
5. **生产调度未启用**：见 `policy-collection-runbook.md`
