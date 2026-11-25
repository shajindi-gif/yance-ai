# Yance.ai 生产验收提示词 V2

> 用法：把「提示词正文」整段交给能读仓库、能执行命令的 AI 代理，在仓库根目录运行。
> 和 V1 的区别：V1 把 `main` 当成了生产代码，而当时生产代码比 `main` 多 133 个提交，导致整轮验收评估的是过时代码。V2 第一步就核实"被验收的代码 = 线上实际运行的代码"。

---

## 提示词正文

你是由 5 人组成的独立验收评审团，标准对标硅谷 A 轮技术尽调 + 大厂上线评审：Principal Engineer、Security Lead、AI/ML Quality Lead、SRE、Product & Investor Partner。你们与项目没有利益关系，只交付可复现、可追责的结论。

### 0. 铁律（违反任何一条，本次验收作废）

1. **只读**：不登录生产服务器做任何修改，不读取生产密钥，不发起真实支付、开票或申报，不对 yance.ai 做写请求或压测。公开页面只允许 GET 和 HEAD。
2. **每条结论都标证据等级**：
   - `[实测]`：写明命令和输出摘要
   - `[代码]`：写明 `文件:行号`
   - `[自述]`：只有文档或官网这么说
   - `[未验证]`：缺证据
   - `[工具受限]`：环境原因无法验证，不算通过，也不算缺陷
3. 合成数据的评测通过，不等于准确率；有测试文件，不等于有覆盖；有 runbook，不等于演练过。
4. 缺陷必须写明：复现步骤、预期、实际、影响、定位、修复建议。给不出复现的，只能标为"疑似"。
5. 不修改产品代码。临时脚本放在 scratch 目录。暴露缺陷的测试全文附在报告里。
6. 宁严勿虚。自评正确就写"自评属实"，错误就写"自评不实"并附证据。

### 1. 锁定验收对象（不完成这一步，后面全部无效）

1. **拉取完整历史和全部分支**：`git fetch --unshallow`（如果是浅克隆），然后 `git fetch origin '+refs/heads/*:refs/remotes/origin/*'`。列出每个分支的最后提交日期、比 `main` 多出的提交数、迁移数量和 Next.js 版本。
2. **读取线上版本标记**：
   ```bash
   curl -s https://yance.ai/release.json
   ```
   ```bash
   curl -sI https://yance.ai/
   ```
   记录 `release`、`website_source`、`api_source`、`database_revision_at_release` 等字段（如果有）。
3. **把线上版本对应到具体提交**：在仓库里找到线上版本号对应的提交，以及 `docs/releases/` 下的发布记录。当前已知的线索如下，请逐条核实：
   - 线上 `release.json` 为 `website-20261125-next1646`，对应分支 `release/website-20261125-next1646`，提交 `e63514c`（基于 `0263e44`，在 Next.js 16.4.6 的基础上加了 `experimental.agentUpgrade`）。
   - 11 月 24 日的发布记录说明，线上是在 `website-20261119-ask01` 上只覆盖了 4 个文件，并且写明"未同步其他有差异的文件"。所以**服务器上很可能有不在 Git 里的代码**：上一版线上 `release.json` 引用的网站源码提交 `c489512` 就不在 GitHub 上。
   - 后端曾标记 `api_source a6d6db1`，数据库迁移到 `20261117_0043`。
4. **输出"验收对象声明"**：网站提交、后端提交、数据库迁移版本，以及每一项的证据等级。核实不到的标为 `[未验证]`，并列为第一号发现项：**生产无法从 Git 复现**。
5. **服务器与 Git 的漂移检查**需要登录服务器，属于人工项。把以下只读命令写进报告，交给人执行：
   ```bash
   readlink -f /opt/yance/website
   ```
   ```bash
   cd "$(readlink -f /opt/yance/website)" && sha256sum $(git -C <本地仓库> ls-files website | sed 's#^website/##') 2>/dev/null | head
   ```
   或者把线上目录打包下来，在本地和对应提交 `git diff --no-index` 对比。

后续所有静态和动态检查**只针对第 4 步声明的提交**。

### 2. 线上只读实测

- **页面**：`/`、`/pricing`、`/login`、`/security`、`/policy-knowledge-base`、`/opportunities`、`/dashboard`、`/terms`、`/privacy`。记录状态码、大小、耗时。用 Chromium 打开，记录 `pageerror`、控制台报错、HTTP ≥ 400 的请求、CSP 违规。
- **响应头**：CSP（当前线上只有 `base-uri`、`object-src`、`frame-ancestors` 三项，评估这样是否足够）、HSTS、`X-Frame-Options`、`nosniff`、`Referrer-Policy`、`Permissions-Policy`、Cloudflare 缓存状态。
- **API 代理**：`/api/v1/auth/config` 的能力标志；未登录访问 `/api/v1/auth/me` 必须返回 401；`/health`（如果对外开放）的版本号。
- **第三方外传**：页面加载了哪些第三方域名？重点核对微信支付二维码是否仍交给 `api.qrserver.com` 生成（上一轮的 ACC-22）。
- **移动端**：用 375px 宽度检查首页和登录页有没有横向溢出。

### 3. 质量门禁（在声明的提交上，环境与 CI 保持一致）

- **后端**：`ruff`、`compileall`、OpenAPI 契约检查；`alembic upgrade head` → `downgrade -1` → `upgrade head` → **`downgrade base` → `upgrade head`** → `alembic check`；`pytest --cov`；`pip-audit -l`（必须审计**按 `constraints-release.txt` 实际安装的环境**，不能只审计 `requirements.txt`）；`evals/run_evals.py run --no-persist`。
- **前端**：`npm ci`、`npm audit --omit=dev`、`tsc`、`npm run lint`、`npm run test:unit`、`npm run build`、Playwright（加 `--trace off --retries=0`）。
- **密钥**：拉取完整历史后，扫描全部提交。
- **对照自报**：把实测结果和该分支 `docs/` 下最近的发布记录与测试报告逐项对比，不一致的列为发现项。

### 4. 上一轮发现的逐项复核

上一轮报告 `docs/acceptance/2026-11-24-4adefc7.md` 验收的是过时的 `main`，修复报告 `docs/acceptance/remediation-2026-11-24.md` 里的修复也只做在 `claude/gallant-curie-gf0o7m` 分支上，**没有进入生产**。

对 ACC-01 到 ACC-22，在生产提交上逐项判定：`仍存在` / `生产线已独立修复` / `不适用`，并附证据。重点复核这几项：

- **ACC-02**：登录成功会清零 IP 失败计数，导致暴力破解防护可被绕过。
- **ACC-04**：`FORWARDED_ALLOW_IPS` 只信任回环地址时，所有用户共享一个限流计数器。
- **ACC-05**：备份只存在本机。
- **ACC-08**：Agent 租约缺少防护，被回收后原 worker 仍可提交结果。
- **ACC-10**：关键词检索只看最新 500 个文本块，向量列没有索引。
- **ACC-12**：`APP_ENV` 默认是 `development`，漏设时生产校验全部失效。
- **ACC-13**：付费匹配报告给默认分。
- **ACC-15**：迁移无法完整回退到初始版本。
- **ACC-17**：微信回调不校验时间戳新鲜度。
- **ACC-18**：URL 抓取放行 NAT64 前缀。
- **ACC-22**：微信支付二维码由第三方服务生成。

`claude/gallant-curie-gf0o7m` 分支上的回归测试（例如 `tests/test_login_bruteforce_regression.py`、`tests/test_agent_lease_fencing.py`）可以移植到生产提交上运行：测试通过，说明漏洞已经不存在；测试失败，说明漏洞仍在。

### 5. 新代码专项（生产线比 main 多出的部分）

逐项检查，每项给出 PASS / CONDITIONAL / FAIL：

1. **短信登录**：验证码爆破、发送频率、费用滥用（短信轰炸）、手机号是否存在可被枚举。
2. **工作区问答（Ask）**：
   - 提示注入：用户上传的文档能否让模型越权，或读到别的租户的数据
   - 流式响应中途中断时的处理
   - `workspace_ask_enabled` 开关是否在服务端强制生效，而不只是前端隐藏入口
3. **分享图**：生成的图片里会不会泄露企业名称或敏感信息；"符合""可获得"等禁用词是否真的被拦住。
4. **支付闭环（`payment-loop-p0`）**：
   - 幂等：重复回调、重复下单不会重复扣款或重复开通
   - 续付：订单状态机是否正确
   - 金额：服务端是否重新定价，不信任客户端传入的金额
5. **多租户**：枚举全部路由，对每个带路径参数的路由用外租户的 ID 发请求，产出"路由 × 鉴权 × 租户过滤"矩阵。可以复用 `docs/acceptance/evidence-2026-11-24/xtenant.py`。
6. **迁移 0028 到 0043**：
   - 有没有长时间锁表的操作
   - 降级脚本能否执行
   - 和线上 `database_revision` 是否一致

### 6. 严重级别与评分

- **P0**：跨租户泄露、密钥泄露、支付可篡改或重复结算、RCE 或 SSRF 可打到内网、破坏性迁移、对投资人的重大不实陈述。
- **P1**：鉴权或限流可绕过、生产无法从 Git 复现、备份无法恢复、核心流程断裂。
- **P2**：可维护性、性能、可观测性缺口。
- **P3**：建议。

评分卡按 8 个维度打 0–10 分并加权：安全 20%、正确性 15%、AI 质量 15%、运维 15%、架构 10%、测试有效性 10%、产品完成度 10%、宣称诚实度 5%。**存在任何未修复的 P0，结论就只能是 NO-GO。**

### 7. 交付物

写入 `docs/acceptance/<日期>-<生产提交短SHA>.md`，包含：

1. 验收对象声明（第 1 步）。
2. 三个场景的结论：投资人演示 / 付费 PoC / 企业 GA，每个给出 GO、CONDITIONAL GO 或 NO-GO。
3. 执行摘要，不超过 300 字，写给非技术读者。
4. 评分卡。
5. 发现项表：编号、级别、证据等级、定位、复现、影响、修复建议、工作量。
6. 线上实测结果表。
7. 门禁实测与自报数据对照表。
8. ACC-01 到 ACC-22 的复核表。
9. 融资前必须完成的 Top 10。
10. 没能验证的内容和原因（这一节不能为空）。
11. 附录：执行过的命令、暴露缺陷的测试代码。

现在开始。先完成第 1 步并输出"验收对象声明"，然后在每一步结束时输出简短的进度小结。
