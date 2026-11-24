# 官网企业向改造 · 本地验收（A）· 2026-11-18

分支：`design/website-enterprise-20261118`（已提交 `f35f380` / `e1e23a5` / `abcf3a6`）。本轮只做验收与小修，未部署生产。

## 保护范围（未纳入本轮提交）

- 政策采集未提交改动与 `candidates/`、`expand_sources.py`
- Workspace Ask 未提交改动（`AnswerWithCitations.tsx`、`ask-stream.ts`、`workspace.py`、`test_workspace_ask_v1.py`、`config.py`）
- `.env.local`（本机已改为同源 `NEXT_PUBLIC_API_URL=/api/v1`，已 gitignore）

## 本轮代码改动

1. `website/app/pricing/PricingCatalogue.tsx`：重载时先清错误态；空目录提示避开加载中误报。
2. `website/e2e/frontend-redesign.spec.ts`：登录用例在邮箱验证码默认开启时，先点「使用邮箱密码登录」再断言密码字段。
3. `website/playwright.chrome.config.ts`：本机 arm64 可用系统 Chrome 跑 e2e（可选配置，不改默认 CI 项目）。

## 验证结果

### Playwright（系统 Chrome + `PLAYWRIGHT_EXTERNAL_SERVER=1`）

通过：

- audience-feedback（4）
- growth-journey industry assets / provider failure（2）
- frontend-redesign：public design、pricing error recovers、login labels

说明：本机 Playwright 官方 Chromium 沙箱装成 x64、arm64 下载易锁；验收用 `playwright.chrome.config.ts` + 本机 Google Chrome。

### 手测 / 脚本（390 / 768 / 1440）

路径：`/`、`/solutions`、`/solutions/investors`、`/pricing`、`/login?register=1&next=%2Fcompanies`

- 无横向溢出
- 首页 H1 含「看清每项条件的依据」；定价 H1「按次购买，需要时再买」
- 390：汉堡菜单可开，末项「免费开始」，Esc 可关
- `/discover` 未登录 → `/login?next=%2Fdiscover`
- 演示链接：`mailto:yanceai@163.com?subject=预约企业演示`
- 定价 503 后「重新加载」：在同源 `/api/v1/products` 下 alert 清除且出现目录卡片

### 未覆盖

- 登录后真实政策扫描、支付下单、生产切换
- 默认 `npx playwright install chromium`（arm64）完整装好后的 CI 同构跑法
- Next.js 16.4.3 安全升级提示（另有 worktree / 需单独确认）

## 结论

| 问题 | 结论 |
| --- | --- |
| 可否提 PR（仅 website 营销 + 本轮小修 + 本验收文档） | **可以**，勿带采集 / Ask 脏文件 |
| 可否申请生产网页切换 | **暂缓**：先合 PR / CI；生产构建须核对 `NEXT_PUBLIC_API_URL` 同源策略与 `API_PROXY_TARGET`；需你显式确认后再部署 |

## 本地复跑

```bash
cd website
# .env.local: NEXT_PUBLIC_API_URL=/api/v1
CI=1 NEXT_TELEMETRY_DISABLED=1 npm run dev -- --webpack --hostname 127.0.0.1 --port 3000
PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 \
  npx playwright test e2e/frontend-redesign.spec.ts e2e/audience-feedback.spec.ts e2e/growth-journey.spec.ts \
  --config=playwright.chrome.config.ts \
  --grep "public design|pricing error|login and registration|homepage broadens|mobile scene|industry assets|authenticated feedback|failed feedback|provider failure"
```
