# backend-20261128-phase-a 发布记录（待执行）

**范围**：只更新后端（API、agent-worker、document-worker），以及备份脚本。不改网站，**没有新的数据库迁移**（仍为 `20261117_0043`）。

**来源**：`feat/phase-a-foundation` 分支。打包前确认分支最新提交与本记录同次提交一致。

**内容**：登录暴力破解防护（ACC-02/07）、只信任回环地址时拒绝启动并在日志记录客户端 IP（ACC-04）、镜像默认生产模式（ACC-12）、拦截 NAT64 地址（ACC-18）、异地备份与恢复演练脚本（ACC-05）、问答免责声明与来源排序修复（N1、N2）。详见 `docs/acceptance/2026-11-28-e63514c-phase-a.md`。

> ⚠️ **最重要的一条**：生产 `production.env` 中的 `FORWARDED_ALLOW_IPS` 如果只有 `127.0.0.1`，**新版后端会拒绝启动**。必须先完成第 2 步。

## 0. 前置条件

- [ ] 服务器上所有不在 Git 里的改动都已提交并推送
- [ ] 已经开通异地备份存储（或者明确接受本次只做本机备份）
- [ ] 选好低峰时段；预留 30 分钟

## 1. 只读核对（不改任何东西）

```bash
ls -1t /opt/yance/releases | head -5
```

```bash
R_OLD=/opt/yance/releases/opportunity-20261119-rank01 && ls "$R_OLD"
```

先确认上一条命令列出了 `activate.sh`、`production.env`、`release.override.json`。如果当前后端目录不是 `opportunity-20261119-rank01`，把 `R_OLD` 换成实际目录名。

```bash
sudo grep -n '^FORWARDED_ALLOW_IPS=' /opt/yance/releases/opportunity-20261119-rank01/production.env
```

```bash
sudo less /opt/yance/releases/opportunity-20261119-rank01/activate.sh
```

记下 `activate.sh` 是用什么方式构建镜像、启动容器的。它如果写死了 `opportunity-20261119-rank01` 这个路径，第 3 步要替换。**看不懂就先停下**，把它的内容（确认里面没有密钥后）发给 Claude。

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep -i yance
```

```bash
docker exec <api 容器名> alembic current
```

期望输出 `20261117_0043 (head)`。不一致就停下。

## 2. 设置 `FORWARDED_ALLOW_IPS`

查出 nginx 所在的 Docker 网络网段：

```bash
docker network ls | grep -i yance
```

```bash
docker network inspect <上一步的网络名> --format '{{(index .IPAM.Config 0).Subnet}}'
```

第 3 步复制配置后，在**新目录**的 `production.env` 里把它设为这个网段，例如 `FORWARDED_ALLOW_IPS=172.18.0.0/16`。**不要用 `*`**，也不要只写 `127.0.0.1`。

## 3. 准备新版本目录

在你的电脑上打包：

```bash
cd ~/yance-backup/yance && git fetch origin feat/phase-a-foundation && git archive --format=tar.gz -o /tmp/backend-20261128-phase-a.tar.gz origin/feat/phase-a-foundation yance-ai && shasum -a 256 /tmp/backend-20261128-phase-a.tar.gz
```

```bash
scp /tmp/backend-20261128-phase-a.tar.gz <服务器>:/tmp/
```

在服务器上解压，并沿用旧版本的配置（只复制文件，不在终端打印内容）：

```bash
R_OLD=/opt/yance/releases/opportunity-20261119-rank01 && R=/opt/yance/releases/backend-20261128-phase-a && sudo mkdir -p "$R" && sudo tar -xzf /tmp/backend-20261128-phase-a.tar.gz -C "$R" && sudo cp -p "$R_OLD/production.env" "$R_OLD/release.override.json" "$R_OLD/activate.sh" "$R/"
```

```bash
sudo sed -i 's#opportunity-20261119-rank01#backend-20261128-phase-a#g' /opt/yance/releases/backend-20261128-phase-a/activate.sh
```

```bash
sudo sed -i 's#^FORWARDED_ALLOW_IPS=.*#FORWARDED_ALLOW_IPS=<第 2 步查到的网段>#' /opt/yance/releases/backend-20261128-phase-a/production.env
```

如果 `production.env` 里原本没有这一行，就追加一行：`echo 'FORWARDED_ALLOW_IPS=<网段>' | sudo tee -a .../production.env`。

## 4. 先备份数据库

```bash
cd /opt/yance/releases/backend-20261128-phase-a/yance-ai && sudo YANCE_DB_CONTAINER=<数据库容器名> YANCE_BACKUP_OFFSITE_URI=<异地地址> bash ops/backup.sh
```

还没开通异地存储时，把 `YANCE_BACKUP_OFFSITE_URI=...` 换成 `YANCE_BACKUP_OFFSITE_DISABLED=true`。看到 `backup ok` 再继续。

## 5. 切换

```bash
sudo bash /opt/yance/releases/backend-20261128-phase-a/activate.sh
```

## 6. 验证

```bash
curl -fsS http://127.0.0.1:8000/health/ready
```

```bash
docker exec <api 容器名> alembic current
```

期望仍是 `20261117_0043 (head)`。

```bash
curl -s https://yance.ai/api/v1/auth/config
```

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://yance.ai/api/v1/auth/me
```

期望返回 `401`。

**核对客户端 IP**（ACC-04）：用手机流量和办公室网络各打开一次 `https://yance.ai/`，然后：

```bash
docker logs --since 5m <api 容器名> 2>&1 | grep request_completed | grep -o '"client_ip": "[^"]*"' | sort | uniq -c
```

应该能看到这两个真实的公网 IP。**如果只看到 nginx 或 Docker 网关的地址，立即回滚**，否则登录和注册的限流会退化为全站共用一个计数器。

最后用浏览器登录一次你的账号，确认能正常进入工作台。

## 7. 回滚（一条命令）

```bash
sudo bash /opt/yance/releases/opportunity-20261119-rank01/activate.sh
```

本次没有数据库迁移，回滚不涉及数据。如果 `activate.sh` 不是"重建容器"的写法，按第 1 步看到的方式切回旧目录。
