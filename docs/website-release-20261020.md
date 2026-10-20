# 网页独立发布：web-20261020-01

2026-10-20，基线 a31f157e7fe789237ed1b5dc276388b1aaad0e71，工作分支 feature/investor-grade-upgrade。

用户要求“用户们能用到最新的网页”，本次发布范围仅 website。后端审计修复、0026/0027 迁移、生产交易与历史数据均不在本次范围。

## 已执行的发布前验证

- 本机 Node 26.8.1 / Next 16.3.8：`npm run typecheck` 和 `npm run build` 通过。
- Chromium，127.0.0.1，无网络节流，独立 PostgreSQL 18 合成库 yance_web_release_test；`PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3018 PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8018/api/v1 NEXT_PUBLIC_API_URL=http://127.0.0.1:8018/api/v1 npm run test:e2e`：7 passed (5.2s)。
- 覆盖登录失败恢复、受支持时的会话撤销、定价加载、移动端基本操作、区县保存刷新、资料控件、DEMO DOCX，以及旧能力响应下的画像保存和本机退出。
- 旧接口兼容测试是合同模拟；真实生产客户流程、真实付款和发票未进行写入测试。
- 生产只读核对：Ubuntu / Node 22.23.2，yance-website 服务端口3000；现有 Next16.3.4；API健康正常；auth/config仅返回 email_login_enabled=true，没有新能力标志。

## 兼容范围

修正页脚链接，升级 Next16.3.8及依赖锁。新增能力须服务端明确声明才显示：区县、取消任务、退出所有设备。当前生产将保留“退出当前设备”，不虚称已撤销其他设备。浏览器 API 使用 `/api/v1` 同源路径；构建时设置 `NEXT_PUBLIC_API_URL=/api/v1`、`API_PROXY_TARGET=http://127.0.0.1:8000`，由网页服务转发到既有后端，避免客户端跨域依赖。配置属于本次发布输入，后端地址只在服务器使用。

## 发布和回退步骤

1. 将仅网页改动及本记录形成固定Git提交，推送功能分支，不推main，避免触发旧版全栈自动部署。
2. 从该提交 git archive website，校验包摘要，放到 /opt/yance/releases/website-web-20261020-01。不得手改运行源码。
3. 仅服务器内部继承既有网页环境文件，不输出其内容；Linux执行 npm ci、typecheck、build、audit。
4. 新构建先监听127.0.0.1:3001；核对页面、静态资源、release.json及只读API。旧网页继续服务。
5. 服务切换到固定新目录，保留旧目录及原服务文件；启动失败或正式域名异常立即恢复原服务。无数据库迁移，不需要数据回滚。
6. 正式域名确认release.json和页面/资源/只读API；浏览器检查定价和登录。记录实际SHA、摘要、构建与线上结果。

后端整批发布仍须满足 docs/release-runbook.md 中的独立门槛。本次网页上线不代表全部审计问题已解决。

## 实际发布结果（已获用户最终确认）

- 用户明确回复“确认，立即发布网页”。2026-10-20 22:16:39（Asia/Shanghai）切换正式服务。
- 已部署源码提交 `ab504587ec0a64b75f5d259084e587ec97c29c9f`，GitHub功能分支已推送；未推main，避免触发旧版全栈自动部署。
- `git archive HEAD website` 源码包 SHA-256：`e3c7b078d7d35f18cb44448951ca21ef1cf886c78aff9c2758c64093873379a0`；服务端校验一致。
- Ubuntu / Node22.23.2 / Next16.3.8，Linux typecheck/build通过，`npm audit --omit=dev --audit-level=high`报告0漏洞。最终同源构建 BUILD_ID：`vYJgmqaqqie_fRRWbVgka`。
- 正式 `yance-website` 服务 WorkingDirectory 为 `/opt/yance/releases/website-web-20261020-01/website`；仅通过systemd drop-in选择版本，没有直接修补服务器源码。
- `/opt/yance/website` 原版保留。原服务文件受限备份 `.../service-before.conf`，SHA-256 `4f06c35134b2d5aefa4ba51037c1477eaa694fa5244cbfeeafd2d9c4842232bc`。新目录额外保留旧内容哈希静态资源，供已有浏览器页面继续请求。
- 切换脚本健康重试中出现一次服务启动前连接拒绝，随后7个本机路由200；正式服务active。自动失败恢复分支未触发，不能说已执行生产回退演练。
- 22:17:35正式域名Chromium五页检查通过：主页、定价、登录、安全、政策库介绍，真实目录加载正常，浏览器pageerror和HTTP>=400记录均为空；样本为每页一次访问，不是SLA。测试拦截2次POST，未提交登录、注册、订单、发票或任务。
- 公网GET主页200，Cloudflare `cf-cache-status: DYNAMIC`；`/release.json`为 `web-20261020-01`，`/api/v1/auth/config`正常，未登录 `/api/v1/auth/me`公网/本机均401。此前公网HEAD及一轮服务器出站连接超时已记录；后续公网GET与浏览器通过，未将超时记录伪称通过。
- API `/health`仍为原 `0.2.0`，未发布后端、迁移数据库、读取客户资料或执行交易。候选3001服务已停止。

证据：`audit-evidence/website-candidate-20261020.json`、`website-production-20261020.json`、`website-activation-20261020.txt`、`website-production-home.png`。复测命令：`YANCE_SMOKE_BASE=https://yance.ai YANCE_SMOKE_OUT=/private/tmp/yance-web-repeat node docs/audit-evidence/website-public-smoke.cjs`（需已安装website依赖与Chromium；始终阻断非只读业务请求）。

### 实际回退命令（仅在验收失败时执行）

```sh
sudo rm /etc/systemd/system/yance-website.service.d/90-website-web-20261020-01.conf
sudo systemctl daemon-reload
sudo systemctl restart yance-website
curl --retry 10 --retry-connrefused --retry-delay 1 -fsS http://127.0.0.1:3000/
```

这只回退本次网页及同源代理配置；无数据库操作。旧网页原有后端安全问题不会因本次网页发布或回退而得到修复。
