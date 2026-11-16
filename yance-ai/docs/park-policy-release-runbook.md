# 园区政策系统 · 发布与运维 Runbook

生产服务器 `43.128.1.64`。本文件区分**可以在本地执行**与**必须获批后在生产执行**。

---

## 0. 当前生产状态：未知（阻塞）

本轮**未在生产做任何变更**。只读核查失败的记录见第 8 节；在拿到只读核查结果之前，本文件所有"生产命令"仅为待执行草案，不代表已验证。

生产变更前置条件（缺一不可）：

- [ ] 固定提交号（当前全部改动未提交，无提交号）
- [ ] Alembic 迁移 upgrade/downgrade 双向往返实测通过
- [ ] 资源预算：CPU/内存/磁盘增量 + 模型日调用预算
- [ ] 备份与恢复实测证据
- [ ] 回退步骤演练
- [ ] 用户书面确认

---

## 1. 本地：无 DB 命令（随时可用）

```bash
cd /Users/shajindi/yance-backup/yance/yance-ai

# 园区目录自检
.venv/bin/python scripts/park_policy/cli.py parks validate
.venv/bin/python scripts/park_policy/cli.py parks summary
.venv/bin/python scripts/park_policy/cli.py parks summary --json

# 按地区/类型筛选
.venv/bin/python scripts/park_policy/cli.py parks list --province 江苏省
.venv/bin/python scripts/park_policy/cli.py parks list --type national_high_tech_zone

# 适用范围解释（只读，不写库，不做资格结论）
.venv/bin/python scripts/park_policy/cli.py parks scope \
  --level park --park-id park_sz_sip \
  --fact address_city=苏州市 --fact address_district=工业园区
# 退出码：0=satisfied，4=not_satisfied/needs_review/insufficient

# 来源目录与连通性（上一轮采集系统）
.venv/bin/python scripts/policy_collection/cli.py validate
.venv/bin/python scripts/policy_collection/cli.py plan
.venv/bin/python scripts/policy_collection/cli.py verify --level national
.venv/bin/python scripts/policy_collection/cli.py coverage --markdown

# 对照评测
.venv/bin/python scripts/park_policy/cli.py eval run \
  --out docs/evidence/eval-report-$(date +%F).json

# 测试
.venv/bin/python -m pytest tests/park_policy tests/policy_collection -q
```

---

## 2. 需要 DB 的命令（本地不可用）

```bash
# 采集单源
.venv/bin/python scripts/policy_collection/cli.py run --source <source_id> --max-items 20
.venv/bin/python scripts/policy_collection/cli.py run --level municipal --limit 3

# 到点任务（cron 实际调用这条）
.venv/bin/python scripts/policy_collection/cli.py run-due

# 六状态覆盖矩阵 / 健康度
.venv/bin/python scripts/policy_collection/cli.py coverage --json
.venv/bin/python scripts/policy_collection/cli.py status

# 暂停 / 恢复 / 重试
.venv/bin/python scripts/policy_collection/cli.py pause <source_id> --reason "站点改版"
.venv/bin/python scripts/policy_collection/cli.py resume <source_id>
.venv/bin/python scripts/policy_collection/cli.py retry --source <source_id>
```

无 DB 时这些命令返回退出码 3 并提示可用替代命令，不会抛栈。

**暂停语义**：`pause` 只停止调度，已入库政策照常可读。这是硬要求。

---

## 3. 初始采集频率（配置化，非硬编码）

| 栏目类型 | 频率 | 说明 |
| --- | --- | --- |
| 国家及重点城市申报栏目 | 6 小时 | 当期窗口变化快 |
| 普通政策栏目 | 每日 | |
| 已开申报窗口的原文与附件 | 每日复核 | 查内容哈希变化 |
| 历史政策 | 每周分批轮巡 | 控制单站压力 |

频率按站点实际规则可下调；`robots` 或 429 触发时自动退避，不靠人工盯。

---

## 4. 迁移（已生成，待真实 PG 验证）

迁移文件已存在于 `alembic/versions/20261106_0037_park_policy_evidence.py`（依赖 `20261106_0036`）。
本机无 PostgreSQL，**升级/回退均未实测**，因此不得部署。

```bash
# 仅在有 PostgreSQL 的环境执行；必须验证双向往返
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1   # 必须能回退
.venv/bin/alembic upgrade head
```

生成后检查：`parks`、`park_policy_scopes`、`policy_conditions`、`policy_eval_runs` 四表；无对既有表的破坏性改动；索引覆盖 `(province, city)`、`(park_type)`、`(policy_id, version)`。

**未验证前不得合并。**

---

## 5. 生产只读核查草案（获批后执行）

```bash
# SSH 保持主机身份校验，禁止 StrictHostKeyChecking=no
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && git log -1 --format="%H %ci %s"'
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && git status --porcelain | head -30'
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && .venv/bin/alembic current'
ssh <user>@43.128.1.64 'systemctl list-units --type=service | grep -i yance'
ssh <user>@43.128.1.64 'df -h / && free -m'
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && .venv/bin/python scripts/policy_collection/cli.py status'
```

只读，不改文件、不重启服务、不写库。

---

## 6. 部署流程（草案，未执行）

```bash
# 1. 生产备份（先备份再动）
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && pg_dump -Fc $DATABASE_URL > /backup/pre-$(date +%F-%H%M).dump'
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && git rev-parse HEAD > /backup/pre-commit.txt'

# 2. 拉取固定提交（只 fast-forward，不 reset 生产未提交改动）
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && git fetch && git checkout <commit_sha>'
# 若生产存在未提交改动：停止，先人工比对，不得 checkout 覆盖

# 3. 迁移 + 重启（先迁移后重启，迁移需可回退）
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && .venv/bin/alembic upgrade head'
ssh <user>@43.128.1.64 'sudo systemctl restart yance-api yance-worker'

# 4. 立即验证
ssh <user>@43.128.1.64 'curl -sf localhost:8000/healthz'
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && .venv/bin/python scripts/policy_collection/cli.py status'
```

**禁止**：直接改生产业务代码；`git reset --hard`；关闭 SSH 主机身份校验。

---

## 7. 回退

```bash
# 代码回退
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && git checkout $(cat /backup/pre-commit.txt)'
# 迁移回退（仅在 schema 变更确认安全时）
ssh <user>@43.128.1.64 'cd /srv/yance/yance-ai && .venv/bin/alembic downgrade -1'
# 数据恢复
ssh <user>@43.128.1.64 'pg_restore -c -d $DATABASE_URL /backup/pre-<ts>.dump'
ssh <user>@43.128.1.64 'sudo systemctl restart yance-api yance-worker'

# 停用采集但保留读取（最小影响回退）
ssh <user>@43.128.1.64 'for s in $(...list enabled...); do .venv/bin/python scripts/policy_collection/cli.py pause $s --reason rollback; done'
```

停用采集后：政策读取、检索、报告全部不受影响。这是必须验证的回退不变量。

---

## 8. 告警

- 先接本地日志与既有监控（`scripts/policy_collection/cli.py status` 已暴露 backlog、失败率、延迟）
- 外发通知（邮件/IM）**需另行确认**，本轮未接
- "新增 0 条"必须能区分：确无更新 / 规则失效 / 抓取失败。`status` 输出三类分别计数

---

## 9. 模型调用预算

- 未配置供应商 → 抽取阶段**明确停用**，不静默降级为"看起来正常但空结果"
- 启用需设每日调用上限与熔断；`evaluation.py` 中 A/B 臂保持 `blocked` 直到预算获批
- 评测报告须记录模型版本、日期、联网方式、费用

---

## 10. 本轮实测记录

| 命令 | 结果 |
| --- | --- |
| `parks validate` | OK，31 条，digest d087f89d |
| `parks summary` | boundary 全 needs_confirmation |
| `parks scope --level province`（跨省） | not_satisfied |
| `parks scope --level province`（同省非省会） | satisfied |
| `parks scope --level park`（仅地址） | needs_review |
| `eval run` | C 臂 21 题 behavior_match 1.0，A/B blocked |
| `pytest tests/park_policy tests/policy_collection` | 118 passed |
| `pytest`（全量） | 既有 DB 依赖测试失败（OperationalError，本地无 PostgreSQL），与本次改动文件无关 |
| 生产只读核查 | SSH 端口开放，主机指纹已取；**未登录**，缺用户名/认证方式与指纹核对，见第 0 节 |
| 迁移文件 | 已生成 0037，**未在真实 PG 验证** |
| 真实原文采集 | 31 个文件 / 5.1MB（nat_gov_policy、nat_most_gfxwj、nat_ndrc_gfxwj、nat_ndrc_tz、city_suzhou_kjj），含 pdf/docx/ofd |
