# 全国政策采集 · 运行手册

适用版本：工作区未提交改动（基线提交 `0c35d70`，分支 `feature/investor-grade-upgrade`）
园区证据层见 `park-policy-release-runbook.md`；两者部署在同一后端，采集为独立进程。

---

## 1. 命令速查

全部命令在 `yance-ai/` 下执行。

```bash
CLI=".venv/bin/python scripts/policy_collection/cli.py"

$CLI validate                      # 校验来源目录（无 DB）
$CLI plan --level national         # 按层级看登记来源
$CLI verify --level municipal      # 只读连通性探测（不写库）
$CLI run <source_id>               # 采集单源
$CLI run --level provincial --limit 5
$CLI retry <source_id>             # 失败重试（不重复入库）
$CLI run-due                       # 跑所有到期的源
$CLI status                        # 健康度、积压、最近运行
$CLI coverage --markdown           # 六状态矩阵
$CLI pause <source_id>             # 暂停调度（已入库政策仍可读）
$CLI resume <source_id>            # 恢复
```

`run` / `retry` / `run-due` / `status` / `coverage` / `pause` / `resume` 需要 DB 与 `DATABASE_URL`。
`validate` / `plan` / `verify` 不需要 DB。

---

## 2. 初始频率

| 栏目类型 | 频率 | 说明 |
| --- | --- | --- |
| 国家及重点城市**申报**栏目 | 每 6 小时 | 窗口短，错过即损失 |
| 普通政策栏目 | 每日 | |
| 已开放申报窗口的原文与附件 | 每日复核变化 | 只判哈希变化，命中才重新解析 |
| 历史政策 | 每周分批轮巡 | 按 `batch_signature` 分批，不全量重跑 |

频率写在来源 YAML 的 `interval_minutes`，以站点 `Crawl-delay` 与实际负载为上限。任何单位调整都要先 `verify` 观察 429。

---

## 3. 上线前必须确认（当前未做）

1. **迁移**：`alembic upgrade head` 会新增 `policy_collection_*` 表（0036 已生成，未在真实 PG 验证）。先在副本库跑一次 upgrade → downgrade → upgrade
2. **服务器只读核查**：`43.128.1.64` 端口 22 开放，`known_hosts` 无该主机记录，`ssh-keyscan` 已取到 RSA/ECDSA/ED25519 指纹但**未登录**。缺用户名与认证方式，且指纹需与云控制台核对后才可写入 `known_hosts`
3. **资源预算**：见第 5 节，需按实际机器规格确认
4. **存储**：`crawler_output` 与 raw store 目录需落在持久盘，不在容器临时层
5. **回退方案**：见第 6 节

未完成以上四项前，**不启动持续采集**，不在生产写数据。

---

## 4. 首次启动顺序

```bash
# 1. 目录校验（无副作用）
$CLI validate

# 2. 小批量只读探测，确认站点仍可访问
$CLI verify --level national --limit 5

# 3. 单源试采（隔离环境），确认原文与附件落盘
$CLI run nat_gov_policy

# 4. 检查解析质量
.venv/bin/python scripts/park_policy/parse_dry_run.py --show 4

# 5. 三层各取一个源试采，通过后再放量
$CLI run prov_zhejiang_kjt
$CLI run city_suzhou_kjj
```

第 3 步之后必须核对：新增条数、`zero_reason`、附件是否留存、是否有 `blocked_by_robots`。

---

## 5. 资源与费用估算（待确认）

| 项 | 估算依据 | 数值 |
| --- | --- | --- |
| 请求量 | 108 源 × 每日 1 次（申报栏目 ×4） | 约 200–400 次/日 |
| 原文存储 | 实测 84 文件 3.1MB（HTML 正文），均值约 37KB；早期含附件的 30 文件批均值 160KB | 全量 108 源按每日 1 篇估算约 4 万文件 / 2–4GB 起，含附件按 5–15GB 预留 |
| 解析耗时 | 单文档 <1s（HTML） | 单轮全量约 10–20 分钟 |
| 向量费用 | 仅在 `new` / `new_version` 时产生 | 需模型供应商配置后按实际 token 计 |
| 模型调用 | 本轮**未启用**，无供应商配置 | 预算与熔断需单独确认 |

以上为量级估算，不是实测账单。真实值需首轮跑完后用 `status` 校准。

---

## 6. 回退

| 场景 | 步骤 |
| --- | --- |
| 采集拖慢在线业务 | `pause` 全部源 → 确认 API 延迟恢复；采集表独立，不清库 |
| 某源规则失效 | `pause <source_id>`，已入库政策不受影响，修适配器后 `resume` |
| 迁移需回滚 | `alembic downgrade -1`（仅删除本轮新增表，不动既有 `policies` / `policy_versions`） |
| 版本回滚 | 部署回上一个 tag；采集表可保留，旧代码不读新表 |
| 数据异常 | raw store 内容寻址不可覆盖，可按哈希回查原始字节；DB 从备份恢复 |

**不删除已采集证据。** 停用采集与删除数据是两件事。

---

## 7. 日常巡检

每日：

```bash
$CLI status            # 失败源、积压、最近运行
$CLI coverage          # 六状态，看"已解析"是否推进
```

关注三项：`zero_reason=rule_broken`（站点改版）、`zero_reason=fetch_failed`（站点故障）、`blocked_by_robots`（规则变化需重新评估）。

告警目前只写本地日志，未接外发通知。外发通知需单独确认渠道。
