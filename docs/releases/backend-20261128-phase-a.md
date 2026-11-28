# backend-20261128-phase-a 发布记录

- **发布分支**：`feat/phase-a-foundation`（头 `b94963eb72fe79b1fd080600d2bf484a3b1e115f`，基于线上 `e63514c`，8 个提交，29 文件 +603/-46）
- **发布范围**：仅后端（`api`、`agent-worker`、`document-worker`）+ 备份脚本；**网站不改**；**无新迁移**（仍为 `20261117_0043`）
- **执行状态**：2026-11-28 已执行，线上验证通过（实测数据见附录 A）

> ⚠️ 本文档原版漏了两件必须做的事，2026-11-28 补入：
> 1. **必须先用 Dockerfile 构建新镜像并打 tag**（`activate.sh` 用 `--no-build` 重建容器，不构建镜像）；
> 2. **必须写 `release.override.json` 的 image / APP_VERSION / APP_SOURCE_REVISION**，并生成 `approved-image.txt`、`SOURCE_REVISION`。
>
> 缺任一项，`activate.sh` 的 version 轮询校验会失败，ERR trap 自动回滚到 `opportunity-20261119-rank01`。

---

## 0. 前置条件（含本次踩到的两个坑）

### 0.1 先确认线上没有未入库的热修

线上曾出现过直接在服务器改代码、Git 里没有对应提交的情况，这类改动会在发版时静默丢失。发版前必须做一次镜像级的文件比对（命令见 1.3），确认「旧镜像里有的文件、新分支里都有；内容有差异的文件、都能在 `git log` 里对上提交」。

**本次核对结论**：旧镜像 `opportunity-20261119-rank01` 与新镜像各 236 个 py 文件，文件集合完全一致（无「旧有新无」），仅 11 个文件内容不同，全部可对应到本分支的提交。**未发现未入库热修，无需回补。**

### 0.2 镜像必须自己先构建

`activate.sh` 的切换动作是 `up -d --no-deps --no-build api agent-worker`，只重建容器、不构建镜像。若只解压源码而不构建新镜像，容器重建后跑的仍是旧镜像，版本轮询对不上 → 自动回滚。构建步骤见第 4 节。

### 0.3 其他

- 异地备份可用（需要异地则把 `YANCE_BACKUP_OFFSITE_DISABLED` 去掉）；
- 选择低峰时段，全程停写约 15–20 秒；
- 服务器磁盘至少留 3G。

---

## 1. 只读核对（不动线上）

### 1.1 确认线上提交

```bash
curl -s https://yance.ai/release.json
# 期望 api_source = a6d6db194536c421c8d9a0387eef97fd0516703e
```

### 1.2 确认容器状态与配置

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
sudo grep -E '^(FORWARDED_ALLOW_IPS|LOG_LEVEL|AGENT_LOG_PROMPTS)=' /opt/yance/releases/sms-20261029-01/yance-ai/.env.prod
```

### 1.3 镜像级文件比对（发现 0.1 所述热修的手段）

```bash
docker run --rm --entrypoint sh yance-backend:opportunity-20261119-rank01 -c \
  'cd /app && find . -name "*.py" | sort | xargs sha256sum' > /tmp/old.txt
# 构建出新镜像后同样导出 /tmp/new.txt，然后：
echo '=== 缺文件（旧有新无）==='
comm -23 <(awk '{print $2}' /tmp/old.txt | sort) <(awk '{print $2}' /tmp/new.txt | sort)
echo '=== 内容变更 ==='
join -j 2 <(sort -k2 /tmp/old.txt) <(sort -k2 /tmp/new.txt) | awk '$2!=$3{print $1}'
```

「缺文件」必须为空；「内容变更」的每一项都要能用 `git log` 解释。对不上的，先补提交再继续。

### 1.4 记录回滚起点

```bash
sudo bash /opt/yance/releases/opportunity-20261119-rank01/activate.sh --help 2>&1 | head -5
sudo ls /opt/yance/releases/opportunity-20261119-rank01/ | head
```

---

## 2. FORWARDED_ALLOW_IPS（必须先确认，否则新后端起不来）

`app/core/config.py` 在有 `FORWARDED_ALLOW_IPS` 环境变量时校验：若只含 `127.0.0.1` / `::1` / `localhost`，直接抛 `ValueError` 拒绝启动（防止 uvicorn 静默忽略 `X-Forwarded-For`）。

**判断标准**：只要 `.env.prod` 里的值**包含 nginx 所在 Docker 网络的网关 IP 或整个网段**即可，不要求改成整个 `/16`。

```bash
# nginx 所在网段
docker network inspect yance-prod_default --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
# 期望：172.18.0.0/16
```

**本次实测**：线上现值为 `FORWARDED_ALLOW_IPS=127.0.0.1,172.18.0.1`，`172.18.0.1` 即 `yance-prod_default` 的网关，已满足要求，**本版未修改**。改动的成本大于收益（改错会连带影响 nginx 自身健康检查）。

---

## 3. 打包与解压

```bash
R=/opt/yance/releases/backend-20261128-phase-a
cd ~/yance-backup/yance
git archive --format=tar.gz --prefix=yance-ai/ -o backend-20261128-phase-a.tar.gz origin/feat/phase-a-foundation
scp backend-20261128-phase-a.tar.gz ubuntu@43.128.1.64:/tmp/
```

服务器上：

```bash
sudo mkdir -p $R && sudo chown $USER:$USER $R && cd $R
tar -xzf /tmp/backend-20261128-phase-a.tar.gz
sed -i "s/opportunity-20261119-rank01/backend-20261128-phase-a/g" activate.sh
# 兜底：把残留的 RANK01 文案也改掉
sed -i "s/RANK01_RELEASE_ACTIVE/PHASE_A_RELEASE_ACTIVE/g" activate.sh
grep -nE 'opportunity-20261119-rank01|RANK01|backend-20261128-phase-a' activate.sh
```

> `activate.sh` 里两处独立的替换串（版本号 + 大写文案），只替换版本号会漏文案，本次已修正。

---

## 4. 构建镜像（本版新增，原文档缺失）

### 4.1 为什么用补丁式

服务器内存约 3.6G，全量 `pip install -r requirements.txt` 有 OOM 风险；本版**无新增依赖、无新迁移**，改动文件集合确定，因此以线上镜像为底座、只覆盖改动文件。

**前提**：该方式仅在「依赖不变 + 迁移不变 + 改动文件已明确」时使用。后续版本一旦改了依赖或全局中间件，必须回到全量构建。

### 4.2 Dockerfile 模板

```dockerfile
# $R/patch/Dockerfile
FROM yance-backend:opportunity-20261119-rank01
WORKDIR /app
COPY app/services/policy_collection/backfill.py ./app/services/policy_collection/backfill.py
COPY app/services/policy_collection/catalog.py  ./app/services/policy_collection/catalog.py
# …按 git diff --name-only 逐个列出
```

底座必须选**线上正在跑的镜像**，换其他 tag 会把别的改动带进来。

### 4.3 构建与逐文件校验

```bash
cd $R/patch
docker build -t yance-backend:backend-20261128-phase-a .

# 校验镜像内源码与分支完全一致（逐文件 sha256）
docker run --rm --entrypoint sh yance-backend:backend-20261128-phase-a -c \
  "find /app -name '*.py' -type f | sort | xargs sha256sum" > /tmp/img.txt
# 与本地分支的哈希清单逐行 diff，必须零差异
```

**本次实测**：镜像 `yance-backend:backend-20261128-phase-a`，ID `6f66347ad62048862ed371755408f2e5348683bfe35be04e195611e0de36052b`，280MB；镜像内 169 个 py 文件哈希与分支源码逐文件一致。

### 4.4 记录审批镜像与源码版本

```bash
docker image inspect --format '{{.Id}}' yance-backend:backend-20261128-phase-a | sudo tee $R/approved-image.txt
echo b94963eb72fe79b1fd080600d2bf484a3b1e115f | sudo tee $R/SOURCE_REVISION
```

这两个文件是 `activate.sh` 的审批凭据，缺失即拒绝执行，不要手写猜测值。

---

## 5. 版本字段（原文档缺失）

### 5.1 `release.override.json`

`activate.sh` 从 `$R/release.override.json` 读每个服务的 `image` 与 `environment`，四项必须同时写对：

- `image` → `yance-backend:backend-20261128-phase-a`
- `environment.APP_VERSION` → `backend-20261128-phase-a`
- `environment.APP_SOURCE_REVISION` → `b94963e`
- 服务条目里不能残留旧 tag（否则 `compose config` 干跑会暴露）

### 5.2 支付服务按实际运行版本 pin

`payment-expiry` / `payment-reconcile` **不能跟主服务一起切到新 tag**。旧 release 的 override 里写的是 `opportunity-20261119-rank01`，但这两个容器实际跑的是 `opportunity-20261118-03`。若跟随 override 切到新镜像，等于顺手把支付服务换了个未验证版本。

**本次做法**：在 `$R/release.override.json` 里把这两个服务显式 pin 回实际运行值：

```json
"payment-expiry": {
  "image": "yance-backend:opportunity-20261118-03",
  "environment": {
    "APP_VERSION": "opportunity-20261118-03",
    "APP_SOURCE_REVISION": "24486c9bc93f92bbc5f390e6efc2551d62544b85"
  }
}
```

（`payment-reconcile` 同上。取值来自 `docker inspect` 的容器实际值，不是猜的。）

### 5.3 干跑

```bash
base=/opt/yance/releases/sms-20261029-01/yance-ai
docker compose -p yance-prod --env-file "$base/.env.prod" \
  -f "$base/docker-compose.prod.yml" -f "$R/release.override.yml" config > /tmp/cfg.json
grep -E 'image: yance-backend' /tmp/cfg.json
```

**期望**：api、agent-worker → `backend-20261128-phase-a`；payment-expiry、payment-reconcile → `opportunity-20261118-03`。

### 5.4 镜像自检

```bash
docker run --rm --env-file "$base/.env.prod" yance-backend:backend-20261128-phase-a \
  python -c "from app.main import app; print('ok')"
```

配置不合法会在这里崩，而不是上线后崩。

---

## 6. 备份

```bash
sudo bash $R/backup.sh
ls -lh /opt/yance-backups/ | tail -3
```

本次产物：`yance_20261128_105557.dump.gz`（80M，本机，`YANCE_BACKUP_OFFSITE_DISABLED=true`）。

---

## 7. 切换

```bash
sudo bash $R/activate.sh 2>&1 | tee /tmp/activate.log
```

ERR trap 会在校验失败时自动调用 rollback 切回 rank01。若日志出现 `PHASE_A_RELEASE_ACTIVE` 即切换流程走完。

---

## 8. 验证

### 8.1 通用项

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E 'api|agent-worker'
curl -s -o /dev/null -w '%{http_code}\n' https://yance.ai/health/ready          # 200
curl -s -o /dev/null -w '%{http_code}\n' https://yance.ai/api/v1/auth/me        # 401
curl -s https://yance.ai/release.json                                            # api_application_version=backend-20261128-phase-a
docker exec yance-prod-api-1 alembic current                                     # 20261117_0043 (head)
```

### 8.2 `LOG_LEVEL=WARNING` 下如何核对客户端 IP（重点）

`app/main.py` 在 `request_completed` 事件里写 `client_ip=request.client.host`，**这是 INFO 级日志**。生产 `LOG_LEVEL=WARNING`，INFO 全被过滤 —— 所以 `docker logs | grep client_ip` 一定查不到，**不要据此判定透传失败**。

正确做法：看 uvicorn 的 access log（由 uvicorn 自己输出，不受应用 `LOG_LEVEL` 影响），格式为 `client_addr - "METHOD path HTTP/1.1" status`：

```bash
docker logs --since 3m yance-prod-api-1 2>&1 | grep -E ' - (GET|POST|HEAD) ' | tail -20
```

判定标准：

| 日志里出现 | 结论 |
| --- | --- |
| 客户端真实公网 IP（IPv4 或 IPv6） | 透传正常，`FORWARDED_ALLOW_IPS` 与 nginx `proxy_set_header` 都对 |
| 只有 `172.18.0.x` | 未生效，回查第 2 节与 nginx 配置 |
| 只有 `127.0.0.1` | 有中间代理在本地回环转了一次，检查是否有额外反代 |

**本次实测**：日志中出现客户端真实公网 IPv6 `2602:f93b:142:a:bc24:11ff:fec5:aa86:0`，判定客户端 IP 透传正常。

补充：若临时需要看应用层 `client_ip` 字段，可把 `LOG_LEVEL` 临时调成 `INFO` 再看，但会显著增加日志量，验证完须改回 `WARNING`，不要长期开着（`AGENT_LOG_PROMPTS=false` 保持不变）。

---

## 9. 回滚

```bash
sudo bash /opt/yance/releases/opportunity-20261119-rank01/activate.sh
```

回滚后按 8.1 复验，并确认 `release.json` 的 `api_source` 已回到 `a6d6db19…`。数据库无新迁移，无需回灌；如需回数据，用第 6 节的 `dump.gz`。

---

## 附录 A：2026-11-28 实测记录

| 项 | 值 |
| --- | --- |
| 发布目录 | `/opt/yance/releases/backend-20261128-phase-a` |
| 源码包 | `/tmp/backend-20261128-phase-a.tar.gz`（sha256 `62b8b29b915f9f3a19aad8be48c929c2aea6d4f277a3bab10e0cce83588e2341`） |
| 镜像 | `yance-backend:backend-20261128-phase-a` / `6f66347ad620…6052b` / 280MB |
| 构建方式 | 补丁式，底座 `opportunity-20261119-rank01`；镜像内 169 个 py 文件哈希与分支一致 |
| 容器 | api、agent-worker 均 `Up (healthy)` |
| 健康检查 | `/health/ready` 200 |
| 迁移 | `alembic current` = `20261117_0043 (head)`，无新迁移 |
| 线上版本 | `backend-20261128-phase-a` / `b94963e` |
| 鉴权 | `auth/me` 返回 401（未登录，符合预期） |
| 首页 | 200 |
| 客户端 IP | 公网 IPv6 `2602:f93b:142:a:bc24:11ff:fec5:aa86:0` 出现在 access log，透传正常 |
| 网站 `release.json` | 两个路径均已同步（`public/` 与 `.next/standalone/public/`） |
| 回滚快照 | `/opt/yance/backups/backend-20261128-phase-a/rollback.services.json` |
| 数据库备份 | `/opt/yance-backups/yance_20261128_105557.dump.gz`（80M，本机） |

**发版中的核对结论**

1. 新旧镜像文件级比对通过：236 / 236 个 py 文件，文件集合一致，仅 11 个文件内容变更（`auth.py`、`workspace.py`、`config.py`、`main.py`、`auth_rate_limit.py`、`url_fetcher.py`、`policy_dates.py`、`rule_seeding.py`、`scheduler.py`、`matcher.py`、`ranking.py`），**未发现未入库热修，无需回补**。
2. 原 override 会让支付服务跟随主服务切换 —— 已在 5.2 固化为「按容器实际运行值 pin」，本次 override 已按实际值改好。

**遗留**

- `payment-expiry` / `payment-reconcile` 实际仍跑 `opportunity-20261118-03`（本次已在 override 中显式 pin，全量 `up -d` 不会再被带走）。代码无支付相关改动，风险低。
