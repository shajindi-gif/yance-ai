> 历史文档：以下为早期 Mac / Tunnel 环境记录，未经本轮核实，不应作为当前生产事实或直接执行依据。当前源码位置由用户明确为 ~/yance-backup/yance；生产副本目标为腾讯云 /opt/yance，发布前必须按 [release-runbook](../../docs/release-runbook.md) 重新验收。

# yance.ai 生产运行手册（Mac + Cloudflare Tunnel 架构）

上线日期：2026-08-09　版本：v0.2.0

## 一、当前架构

```
用户浏览器 (HTTPS)
   │
Cloudflare（DNS + CDN + WAF + 自动HTTPS）
   │  yance.ai / www.yance.ai ──→ Cloudflare Tunnel ──→ localhost:3000  Next.js 官网（含登录/仪表盘）
   │  api.yance.ai            ──→ Cloudflare Tunnel ──→ localhost:8000  FastAPI（Docker: yance-prod）
```

- 隧道：`yance-ai-tunnel`（ID 55fd8164-a28d-49b7-b5cd-cb518512eb83），配置在 `~/.cloudflared/config.yml`
- 后端：Docker Compose 项目 `yance-prod`（PostgreSQL16+pgvector / migrate / api），仓库 `docker-compose.prod.yml`，环境变量 `.env.prod`
- 前端：`/Users/shajindi/AI-Workspace/qoder 项目1/website`（Next.js 14 生产构建，`next start -p 3000`）
- 本机无公网入站端口；数据库与 API 均仅绑定 127.0.0.1

## 二、常驻服务（launchd，开机自启 + 崩溃自动拉起）

| Label | 作用 | 日志 |
|---|---|---|
| `ai.yance.cloudflared` | Cloudflare 隧道 | `~/Library/Logs/yance-cloudflared*.log` |
| `ai.yance.website` | Next.js 官网（127.0.0.1:3000） | `~/Library/Logs/yance-website*.log` |
| `ai.yance.docker-autostart` | 开机自动拉起 Docker（带重试验证脚本 `~/Library/Application Support/yance-ops/docker-up.sh`） | `~/Library/Logs/yance-docker-autostart*.log` |


> ⚠️ 2026-08-12 教训：系统重启后曾掉线——`ai.yance.website.plist` 丢失、Docker 未自启。已全部恢复并加固自启脚本。**根本解决依赖独立服务器迁移**，Mac 单机方案务必保持开机+已登录+关闭自动睡眠。

Docker 容器（`yance-prod-db-1` / `yance-prod-api-1`）均为 `restart: unless-stopped`，Docker Desktop 启动后自动恢复。

常用命令：

```bash
# 查看服务
launchctl list | grep ai.yance
docker compose -f docker-compose.prod.yml ps

# 重启单个服务
launchctl kickstart -k gui/$(id -u)/ai.yance.website
docker compose -f docker-compose.prod.yml restart api

# 查看后端日志
docker compose -f docker-compose.prod.yml logs --tail=100 api

# 完全重启后端
cd ~/Desktop/部署/yance-ai
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## 三、账号与密钥位置

- 生产 Owner：`admin@yance.ai`（密码保存在 QoderWork 工作区 `.yance-owner-cred`，首次登录后建议尽快改密码）
- `.env.prod`：JWT_SECRET / BOOTSTRAP_TOKEN / TENANT_PROVISIONING_TOKEN / OSS / 支付密钥（chmod 600，勿提交 git）
- 开通新租户（商务交付时，服务器本机执行）：

```bash
cd ~/Desktop/部署/yance-ai && set -a && . ./.env.prod && set +a
curl -X POST http://localhost:8000/api/v1/auth/provision-tenant \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-Provisioning-Token: ${TENANT_PROVISIONING_TOKEN}" \
  -d '{"tenant_name":"客户公司名","tenant_slug":"customer-slug","owner_email":"owner@customer.com","owner_name":"负责人","owner_password":"至少12位强密码"}'
unset TENANT_PROVISIONING_TOKEN
```

前端注册页已移除（B6 修复）：租户开通只走上面的服务端流程，Provisioning Token 不再暴露给浏览器。

## 四、数据与备份

- 生产数据卷：`yance-prod_yance_pgdata_prod`（PostgreSQL）与 `yance-prod_yance_invoices_prod`（发票PDF）
- 已灌入 8 条精选政策（国家/上海市/徐汇区级），语义搜索可用；后续通过 `POST /api/v1/policies` 持续补充
- 建议每周备份（示例）：

```bash
docker exec yance-prod-db-1 pg_dump -U yance yance_prod | gzip > ~/Documents/backups/yance-prod-$(date +%F).sql.gz
```

## 五、上线时修复的问题

- B1 向量维度：迁移 0005 将 `policies.embedding` 对齐为 vector(1024)
- B2 前端挂载：`app/main.py` 的静态挂载改为条件判断，生产镜像无 `/app/frontend` 也能启动
- B6 Token 暴露：前端移除注册流程与 `NEXT_PUBLIC_PROVISION_TOKEN`
- Compose 项目名隔离：`yance-prod` / `yance-dev`，双栈并存不再互相覆盖

## 六、已知限制与下一步

1. 服务依赖这台 Mac 保持开机联网（合盖睡眠会中断服务）；建议系统设置关闭自动睡眠
2. 正式扩客户前迁移到独立服务器（腾讯云HK或阿里云，见 `明日部署手册.md`），把 `api` 指向新服务器、Cloudflare Tunnel 只留过渡
3. 官网如需回到 Vercel 托管：在 Cloudflare 面板把 yance.ai/www 记录改为 A→76.76.21.21、CNAME www→cname.vercel-dns.com，并从隧道 ingress 移除这两条
4. 待办：支付宝支付回调公网验证、公开注册流程（含风控）、LLM 多供应商接入、RDS 化
