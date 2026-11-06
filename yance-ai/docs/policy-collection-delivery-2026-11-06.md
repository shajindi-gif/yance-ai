# 政策证据库 · 交付说明（2026-11-06）

本文是这一轮的**交付凭证**，不是计划书。文中每个数字都来自本机真实 PostgreSQL 实例
上的实际运行，可按下文命令复现；没做到的事写在最后一节，不做模糊表述。

- 固定版本：**`1de3642`**（本轮，历史回填队列 + 增量调度 + 关键词检索接入 + 采集容器化）
  上一轮基线为 `b654ff9`
- 数据库：本机 PostgreSQL 18（`127.0.0.1:55432`），独立库 `yance_prodtest`
- 生产影响：**零**。腾讯云 `43.128.1.64` 未登录、未部署、未改任何配置

---

## 1. 真实 PostgreSQL 测试结果

以下全部在**真实 Postgres**（非 SQLite、非 mock）上执行，库为 `yance_prodtest`。

### 1.1 迁移：upgrade / downgrade 双向验证

从采集系统上线前的基线 `20261031_0035` 升到 head：

```
$ alembic upgrade head
Running upgrade 20261031_0035 -> 20261106_0036, Additive tables for the continuous policy collection system.
Running upgrade 20261106_0036 -> 20261106_0037, Additive tables for the park policy / evidence system.
Running upgrade 20261106_0037 -> 20261106_0038, Lexical search indexes for the policy evidence base (pg_trgm).
$ alembic current
20261106_0038 (head)
```

回退路径也逐一验证过（这是"能不能回退"的唯一证据，不是推断）：

| 回退目标 | 结果 | 说明 |
| --- | --- | --- |
| `0038 → 0037` | 成功，trgm 索引计数变 0 | 只删索引，不动表 |
| `0037 → 0036` | 默认**拒绝**，需 `PARK_POLICY_ALLOW_DROP=1` | 刻意设的闸：园区表里有手工核验数据，误删不可恢复 |
| `0037 → 0036`（带闸） | 成功，`park%` 表计数变 0 | 验证闸门开关本身可用 |
| 再次 `upgrade head` | 成功，回到 `0038` | 升降级可反复执行，迁移是幂等的 |

新库从零建表：`alembic upgrade head` 跑完 38 个迁移，`public` schema 共 91 张表。

### 1.2 重复入库：同一文档不会产生第二条记录

同一源、同一页再抓一次（`run --source nat_mof_policy --max-items 12`）：

```
[run ] nat_mof_policy status=no_update new=0 updated=0 unchanged=12 failed=0
```

- `new=0`：没有新建策略
- `unchanged=12`：12 篇内容哈希一致，判定为未变更
- 表计数未翻倍（`policies` / `policy_versions` / `policy_chunks` 不变）
- 全库重复 URL 检查：`dup_urls = 0`

内容**变化**时才产生新版本，旧版本保留（`test_store_db.py::test_changed_content_creates_new_version_and_keeps_old`）。

### 1.3 断点恢复：kill -9 之后不丢页、不重复

真实进程被强杀，不是模拟：

| 步骤 | 观测 |
| --- | --- |
| 起始 | 游标 `page=3`，`policies=161` |
| 启动批次，7 秒后 `pkill -9` | 游标仍 `page=3`，`policies=161` |
| 续跑同源 | 日志 `pages 3-5`（从游标处继续），游标未回退 |
| 结果 | `dup=0`，无半写记录 |

结论：游标只在整页处理完成后提交，被杀时未完成的那一页不会留下"半页"状态，下次从
同一页重读（重读幂等，见 1.2）。

另一个真实中断留了证据：一次批次在写库时因 PDF 二进制含 NUL 字节整批回滚，事后核对
`policies`/`versions` 均未变化 —— 事务回滚确实生效，没有污染。

### 1.4 检索：能查、能引用、能限地域、不跨租户

关键词检索（`pg_trgm`，**不需要任何模型**）：

```
$ curl '/api/v1/policies/evidence-search?q=研发费用加计扣除&limit=3'
status: 200
count: 3
corpus: {'published_policies': 0, 'searchable_policies': 191, 'versions': 191,
         'chunks': 949, 'embedded_chunks': 0,
         'keyword_searchable': True, 'vector_searchable': False}
  - 研发费用加计扣除项目鉴定案例（第三辑） | span 0 - 876
  - 科技部 财政部 国家税务总局关于进一步做好企业研发费用加计扣除政策落实工作的通知 | span 0 - 810
  - 关于进一步完善研发费用税前加计扣除政策的公告 | span 0 - 890
```

每条命中带 `policy_id` / `version_id` / `chunk_id` / `char_start` / `char_end`，所以引用
可以回到不可变版本的原文位置复核；`review_state` 明确标出该文档是否经过人工复核。

延迟实测（191 篇 / 949 分块，本机）：`研发费用加计扣除` 259 ms、`知识产权` 35 ms、
单字词 34 ms。这是小语料上的数字，不代表 10 万篇时的性能。

同时刻的边界行为（均有测试）：

- 地域过滤不串省：`test_keyword_search_region_filter_does_not_leak_other_provinces`
- 过期政策不进"当前有效"：`test_keyword_search_current_only_excludes_expired`
- 新版本优先、旧版本仍可读：`test_newer_version_wins_in_search_and_old_version_still_readable`
- 跨租户零泄漏：`test_private_documents_never_leak_across_tenants`
- 未认证不能查：`test_evidence_search_requires_authentication`

### 1.5 测试套件

```
$ pytest tests/policy_collection -q
120 passed
```

其中 `test_scheduler.py`、`test_backfill_guards_db.py`、`test_store_db.py`、
`test_keyword_search_db.py`、`test_evidence_search_api.py` 需要真实库，全部在
`yance_prodtest` 上跑通；纯逻辑测试（URL 守卫、robots、抽取、分页发现）无库也能跑。

---

## 2. 本轮修掉的真实缺陷（都是实测撞出来的，不是预设项）

| # | 现象 | 根因 | 修法 |
| --- | --- | --- | --- |
| 1 | 整批采集失败：`PostgreSQL text fields cannot contain NUL (0x00) bytes` | 部分站点把 PDF 当列表项（`downfile.jsp?...filename=x.pdf`），被当 HTML 解码后 25 万字符二进制写进 `policies.content` | 按 `Content-Type`/URL 后缀识别二进制文档，走 `parse_document` 解析；入库前剥离 NUL 与控制字符 |
| 2 | 采集了 148 篇，检索却 0 命中 | 检索 SQL 硬编码 `p.status='published'`，而采集写入的是 `collected`（未人工复核） | 检索支持 `published + collected`，命中结果带 `review_state`，明确标注"未复核" |
| 3 | 搜 5 条结果里只有 3 篇文档 | 分块级返回，同一文档的多个分块占满结果位 | 按 `policy_id` 去重取最高分分块，并返回 `matched_chunks` |
| 4 | `alerts` 命令直接崩：`NameError: result` | 增量调度主开关的短路代码被误粘进 `alerts()` | 改为在告警里汇报 `collection_disabled`，不再返回未定义对象 |
| 5 | 空页源每轮空转，日志看着"在干活" | 空页保守停住游标（正确），但没有次数上限 | 连续 3 次空页后把游标**停放**（`backfill_blocked`）+ 告警，人工修复后用 `backfill-reset` 放行。**停放不等于跳过**：archive 从未被标记为已读完 |
| 6 | 本机所有域名解析到 198.18.0.0/15（TUN/fake-IP），SSRF 守卫把全部请求拦下 | 本机代理的 fake-IP 与"保留网段必须拒绝"的规则冲突 | 加 `POLICY_COLLECTION_DNS_PROXY_CIDRS`（默认空、生产必须空），只对 RFC 2544/5737 这几段放行，且只对**DNS 解析结果**放行，literal IP 一律拒 |
| 7 | 想停采集只能改 env 重启进程 | 全局暂停此前只由 `policy_collection_paused` 环境变量控制 | 加卷上 `PAUSED` 标志文件，`pause --global` 一次生效；标志不可读时**失败即暂停**（fail closed），不会误恢复抓取 |

第 6 条要说明清楚：本轮实测时本机 DNS 已恢复真实解析（`www.cnipa.gov.cn →
221.204.95.167`），下载不依赖这个开关；开关保留是为了下次遇到同样环境能本地联调，
默认关闭，生产文档写明必须留空。

---

## 3. 服务器部署：采集单独跑，资源封顶，原文持久化

### 3.1 为什么单独一个 compose 文件

`docker-compose.collector.yml` 只做一件事：把采集和登录/支付/报表的容器隔开。采集
被限死在 1 CPU / 768 MB，它再疯也抢不到 API 的资源；停采集不会停站。

```yaml
# 关键片段（完整文件见仓库根）
services:
  collector:
    environment:
      POLICY_COLLECTION_ENABLED: "true"          # 主开关
      POLICY_COLLECTION_RAW_DIR: /app/policy_raw # 原文落持久卷
      POLICY_COLLECTION_MIN_FREE_DISK_MB: "3000" # 低于此值停止新增下载
      POLICY_COLLECTION_DNS_PROXY_CIDRS: ""      # 生产必须留空
    volumes:
      - yance_policy_raw_prod:/app/policy_raw
    cpus: "1.0"
    mem_limit: 768m
    pids_limit: 256
    stop_grace_period: 120s
    restart: unless-stopped
```

原文卷 `yance_policy_raw_prod` **命名独立于应用卷**：`docker compose down -v` 应用栈不会
连带删掉采集到的原文。

### 3.2 进程入口

`python -m app.workers.policy_collector`：

- 循环跑调度周期，每周期写入 `collector_state.json` 心跳（容器 healthcheck 读它）
- 单周期有预算上限（默认 600s），循环本身不排队堆积
- 收到 SIGTERM 在**文档之间**停，让当前页写完、游标提交
- 数据库重启导致的会话失效不会杀死进程，下一周期重连
- 主开关关闭时明确告警 `policy_collector_disabled`，而不是静默空转

本机实测一个周期：

```
$ python -m app.workers.policy_collector --once
{"stop_reason": "max_sources", "ran": 2, "skipped": 0, "due_after": 76, "event": "policy_collector_cycle"}
$ python -m app.workers.policy_collector --status
{"status": "running", "stop_reason": "max_sources", "ran": 2, "due_after": 76,
 "storage": {"ok": true, "free_mb": 27465, "threshold_mb": 2048, ...}}
```

非容器环境用 `ops/systemd/yance-policy-collector.service`（含 `CPUQuota=100%`、
`MemoryMax=768M`、`ReadWritePaths` 只放开原文目录）。两条部署路径二选一，不要同时上。

### 3.3 一键运维脚本

`ops/collector.sh`（`bash -n` 通过，`alerts`/`progress` 已实跑）：

| 命令 | 作用 |
| --- | --- |
| `./ops/collector.sh status` | 容器状态 + 心跳 + 积压 |
| `./ops/collector.sh progress` | 逐源回填游标 + 可检索语料数 |
| `./ops/collector.sh start` / `stop` | 启停采集（stop 等在途文档写完） |
| `./ops/collector.sh pause "原因"` / `resume` | 全局暂停/恢复：写卷上的 `PAUSED` 标志，**下一周期生效、不用重启**；暂停期间已采内容照常可检索 |
| `./ops/collector.sh trial 100` | 有界试采，按文档数和墙钟双重限制 |
| `./ops/collector.sh retry <source>` | 单源重试 |
| `./ops/collector.sh reset <source> [--page N]` | 清停放/卡死游标 |
| `./ops/collector.sh alerts` | 持续失败、空页缺口、低磁盘、开关关闭 |
| `./ops/collector.sh backup [dir]` | `pg_dump` + 原文卷打包（缺一份都不算备份） |
| `./ops/collector.sh rollback <ref>` | 停采集 → 切版本 → 应用栈拉起 |

---

## 4. 试采结果与扩容路径

### 4.1 已完成的试采（本机真实库）

| 指标 | 数值 |
| --- | --- |
| 独立政策文件 / 申报通知 | **191** 篇（去重 URL 191，重复 0） |
| 其中政策文件 `policy` | 139 |
| 申报通知 `application_notice` | 6 |
| 清单类 `public_list` | 20 |
| 实施细则 `implementation_rule` | 16 |
| 废止 `repeal` | 6 |
| 其他（解读/延期） | 4 |
| 附件 | 160 个（75 篇带附件） |
| 历史版本（超出首版的版本数） | 0 |
| 正文分块 | 949 |
| 可检索记录 | 949 分块（关键词检索可用，向量 0） |
| 原文落盘 | 226 个原始文件，4.9 MB |
| 发布日期缺失 | 0 |
| 地域缺失 | 0 |
| 层级分布 | national 161 / municipal 30 |
| 年份分布 | 2026:136、2025:24、2024:9、2023:7、2022 及更早:7 |

统计口径按你的要求分开：**10,000 份目标只计"独立政策文件 + 独立申报通知"**，附件、
分块、历史版本单列，不凑数。

注意两个必须一起看的事实：只有 6 篇是 `application_notice`，因为本轮优先采的是
政策文件栏目；`published_policies = 0` 是因为这些文档都还没有过人工复核，检索里一律标
`review_state = unreviewed`。

### 4.2 10,000 篇的实测投影（不是估算表）

用已采到的 191 篇实测，再用 `capacity_probe.py` 按同一比例外推：

| 项 | 实测单篇 | 10,000 篇投影 |
| --- | --- | --- |
| HTML 原文 | 21.6 KB（P90 39.7 KB） | 206 MB |
| 附件 | 274 KB/篇（平均 0.84 个/篇） | 2.08 GB |
| 合计占盘 | — | **2.28 GB**（可用 26.8 GB，余量 24.5 GB） |
| 正文 | 3,868 字符 | 3,868 万字符 |
| 解析耗时（CPU） | 2.5 ms/篇 | 约 0.01 小时 |
| 请求下限（限速 1s/请求） | — | 约 2.8 小时 |
| 嵌入 tokens | 2,417 tokens/篇 | 2,417 万 tokens |

请求下限那 2.8 小时是**纯限速**算出来的，不含重试、退避和失败重跑，所以它是地板不是
承诺。**费用一栏始终为空**：脚本在没有给出单价时不报价，避免拿估算当账单。要算钱请给
单价后重跑：

```bash
python scripts/policy_collection/capacity_probe.py --price-per-mtok <单价> --disk-free-gb 26.8
```

### 4.3 从 100 → 1,000 → 10,000 的实际步骤

```bash
# 第一步：试采（已完成 191 篇，这一步可重复）
./ops/collector.sh trial 100

# 第二步：确认网页能检索（这是扩容的前置条件，不是可选项）
curl -s 'http://127.0.0.1:8000/api/v1/policies/evidence-search?q=研发费用加计扣除&limit=3' \
  -H "Authorization: Bearer <token>" | head -c 600

# 第三步：扩到 1,000（分批跑，每批有界）
for i in $(seq 1 10); do
  python scripts/policy_collection/cli.py backfill-run \
    --enable-collection --max-sources 10 --pages 3 --docs 20 --seconds 1800
done

# 第四步：扩到 10,000（交给调度器持续跑，不再人工分批）
./ops/collector.sh start        # 增量队列常驻
# 历史回填继续靠 backfill-run 分批推进，游标自己记进度
python scripts/policy_collection/cli.py backfill-status   # 随时看进度
```

每一档先看两件事再往上走：`backfill-status` 里游标是否在推进、
`evidence-search` 是否还能召回新语料。

---

## 5. 明确没做 / 做不了的（阻塞项）

| 项 | 状态 | 需要什么 |
| --- | --- | --- |
| 腾讯云生产部署 | **未做**。只做过只读探测，未登录 | 服务器认证方式（密钥或密码）。本轮所有验证都在本机完成 |
| 生产库迁移 | **未做**。生产 PG 仍停在 `0034` | 部署窗口 + 备份确认 |
| 向量检索 | 未启用。`embedded_chunks = 0` | 模型供应商 API Key + 每日预算上限；未配置前不写假向量 |
| 检索评测（Recall@K / 引用支持率） | 未跑，结论仍是 **insufficient** | 同一套模型配置；评测集已建（`docs/policy-retrieval-evaluation.md`） |
| 10,000 篇实际入库 | 未达。当前 191 篇 = 目标的 1.9% | 时间与带宽；命令见 4.3，无需新代码 |
| 园区边界核验 | 31/31 仍 `needs_confirmation` | 官方边界文件或人工逐条核验 |
| 模型费用 | 无法报价 | 单价（缺单价时脚本拒绝编造） |
| PDF/DOCX 之外的 OFD、WPS 解析 | 部分站点的 `.wps` 附件只存原文不解析 | 解析器扩展（不影响原文留存与检索） |

---

## 6. 复现本文所有数字

```bash
cd /Users/shajindi/yance-backup/yance/yance-ai
export DATABASE_URL="postgresql+psycopg://yance@127.0.0.1:55432/yance_prodtest"

# 1) 迁移（含回退）
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade 20261106_0037      # 只删索引
.venv/bin/alembic upgrade head

# 2) 测试（120 passed）
.venv/bin/python -m pytest tests/policy_collection -q

# 3) 试采 + 检索
POLICY_COLLECTION_ENABLED=true ./ops/collector.sh trial 100
./ops/collector.sh progress

# 4) 容量投影
.venv/bin/python scripts/policy_collection/capacity_probe.py --disk-free-gb 26.8
```

---

## 7. 一句话结论

采集链路已经在**真实数据库**上闭环：能持续采、能断点续、不重复入库、原文可追溯、
不配模型也能检索；容器化部署方案与回退命令已就绪，资源与磁盘都有硬上限。
**尚未发生的是生产部署和 10,000 篇的实际积累**，这两件都需要你给服务器访问方式后
才可以开始，我不会把它们写成"已完成"。

*（内容由AI生成，仅供参考）*
