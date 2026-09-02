# 前端审计

## 总评

前端已经达到“完整官网 + 可点击工作台 Demo”的视觉广度，但还不是企业 SaaS 前端。最大问题不是审美，而是页面对后台能力的表达超前、登录态和数据请求全在客户端、关键 API contract 漂移、应用信息架构缺失、没有测试与可观测性。

## 技术基线

- Next.js 14 App Router、React 18、TypeScript。
- 依赖只有 Next/React/ReactDOM；没有表单验证、server state、auth SDK、analytics、测试、组件库或错误监控。
- 约 6,226 行 TSX；`website/app/globals.css` 单文件 5,357 行。
- 根 layout 无条件渲染 Header、Footer 和 SmartAgent，因此登录、结账、工作台和任务页仍背负营销站 shell（`website/app/layout.tsx:35-58`）。
- 受保护页面依赖 `useEffect` 检查本地 token 后 redirect；没有 Next middleware 或 server-side guard。

## 页面清单与真实度

| 页面组 | 现状 | 主要问题 | 优先级 |
|---|---|---|---|
| 首页/About/Parks/Roadshow/Demo | 内容丰富的营销页 | 能力和结果声明缺 proof/link/source；多为静态 UI | P1/P2 |
| Login/Onboarding | 可注册、登录、创建基础企业 | 公共注册与运维文档冲突；无验证邮件、重置密码、条款同意记录 | P1 |
| Dashboard | 企业、报告、订单、统计的单页工作台 | 首个企业被硬选；demo pay；无资料、证据、协作、设置 | P0/P1 |
| Policies/Knowledge Base | 列表与静态样例 | 未登录显示硬编码政策；登录后通过生成报告取列表，产生费用和脏数据 | P1 |
| Tasks/Task detail | 任务、进度、运行、交付 | 后端非持久执行且 schema 漂移；UI 会把假质量分展示为事实 | P0/P1 |
| Reports/Checkout/Orders | 购买和下载 | 主动调用 demo pay；真实支付 contract 不匹配 | P0 |
| Downloads/Chrome extension | 渠道宣传 | Chrome v1.0.0 被标记 available，但无可下载产物 | P0 |
| Security/Privacy/Terms | 法务与信任页 | 多项声明与实现/证据不符 | P0 |

## API Contract 缺陷

| 优先级 | Contract 漂移 | 前端 | 后端 | 结果 |
|---|---|---|---|---|
| P0 | 演示支付被当正式支付 | `api.ts:296-313`，Dashboard/Checkout/Reports 调用 | `/payments/demo-pay` 直接 paid + entitlement | 可零成本解锁交付并制造收入记录 |
| P1 | 支付宝入参/返回值不一致 | JSON `{order_id}`，期待 `{pay_url}` `api.ts:273-279` | query param `order_id`，返回 `{url}` `payments.py:76-138` | 标准结账失败 |
| P1 | 报告入参/返回类型不一致 | 发送 `company_id` 并声明 `Report` `api.ts:232-255` | 仅接收 `query/limit`，返回 query/matched_policies/report/model/provider | 类型保护失真，company_id 被忽略 |
| P1 | global policy 类型不兼容 | `Policy.tenant_id: string` | 全局 Policy 的 tenant_id 可为 null，`PolicyOut` 也错误地非空 | 一旦 API 返回全局政策会校验/类型失败 |
| P2 | 多页绕过统一 request helper | 页面内直接 `fetch` | 认证、错误格式和 retry 不一致 | 401/5xx 被吞掉或展示空白 |

## 安全审计

### P0/P1

- JWT 存储在 `localStorage`（`website/lib/api.ts:69-98`），一旦 XSS 可直接窃取 bearer token；没有 refresh rotation、设备 session 或撤销。
- `next.config.js` 为空，没有仓库可证明的 CSP、frame-ancestors、referrer-policy、permissions-policy 等安全头。
- Google Fonts 由客户端直连；隐私页没有披露该第三方请求，也没有 consent 管理。
- 仅客户端 redirect 会先下载和渲染受保护页面 bundle；安全边界最终虽在 API，但用户体验和缓存策略不可控。
- SmartAgent 的硬编码政策结论没有来源、时间或“模拟数据”标记；API 异常也静默变成确定性回答。

### 建议

- 使用 BFF 或同源 HttpOnly/Secure/SameSite session cookie；短期至少收紧 CSP，并禁止 token 进入 localStorage。
- 营销和应用拆 layout；应用 route group 由 middleware/server session guard 保护。
- 所有 HTML/Markdown 渲染采用安全组件和 allowlist；不要使用任意 HTML。
- 法务、cookie、第三方资源和 analytics 与真实数据流对齐。

## 可用性与企业体验

### 关键缺口

- 没有组织切换、成员邀请、角色管理、SSO、账单管理员。
- 没有文档中心、上传进度、解析状态、字段确认、证据 viewer。
- 没有政策详情页、原文版本、来源链接、页/段引用和变更记录。
- 没有 case workspace：材料、任务、负责人、截止日、审批、评论、活动流。
- 没有通知中心或邮件偏好。
- 没有 Admin、support impersonation（受审计）、失败任务重试、内容发布。
- 错误、空状态和 skeleton 由各页自行处理；无 root error boundary、loading route、not-found 策略。
- 多处 `any`，页面有大段 inline style，复用和可访问性验证困难。

## 性能与 SEO

| 优先级 | 问题 | 说明 |
|---|---|---|
| P1 | 登录后 policies 页面触发完整 match + LLM | 列表浏览产生外部模型成本、重复 Opportunity 和慢请求 |
| P2 | 全站加载 SmartAgent 客户端 bundle | 所有页面，包括法务与登录页，均承担交互组件 |
| P2 | 全局 CSS 和大页面组件 | `globals.css` 5,357 行，首页约 700 行；难以 tree-shake 和独立演进 |
| P2 | Google Fonts 外链 | 增加第三方依赖、隐私与中国网络可用性风险 |
| P2 | SEO 基础不完整 | 有 metadata/OpenGraph，但无 sitemap、robots、canonical 策略、结构化数据、真实 OG 图 |
| P3 | 使用原生 `<img>` | 未利用 `next/image` 的尺寸、优化和 loading 能力 |

## 测试与前端工程

当前 `package.json` 没有 lint、typecheck、unit、component、e2e 或 accessibility script，仓库也没有测试文件。Phase 0 安装锁定依赖后执行 `npm run build`：Next.js 14.2.35 的 25 个页面编译、类型检查和静态生成通过，但 Google Fonts 下载/优化失败。`npm audit --omit=dev` 报告 Next.js、PostCSS、nanoid 共 3 个 High；修复建议会升级到有 breaking change 的 Next.js 版本，必须在独立升级阶段验证，禁止直接 `--force`。

前端 Dockerfile 复制 `.next/standalone`，但 `next.config.js` 没有 `output: 'standalone'`；本次 build 后该目录不存在，因此“本地 Next build 通过”不等于“当前 Docker 镜像可构建运行”。

最低发布 Gate：

1. `npm ci` + `next build`；
2. ESLint + `tsc --noEmit`；
3. Vitest/Testing Library 覆盖 API client、auth、金额/状态和证据组件；
4. Playwright 覆盖注册/登录、企业导入、政策判断、任务审批、真实 sandbox checkout；
5. axe 可访问性和关键页面视觉回归；
6. API schema 自动生成 TypeScript client，CI 检测 contract drift；
7. Docker standalone build smoke test。

## 建议前端结构

```text
website/
  app/
    (marketing)/          # 官网、案例、定价、法务
    (auth)/               # 登录、邀请、重置
    (app)/                # 工作台 shell + server guard
      opportunities/
      companies/[id]/
      cases/[id]/
      tasks/[id]/
      billing/
      settings/
    (platform-admin)/
  features/               # 领域功能组件与 hooks
  components/ui/          # 设计系统
  lib/api/generated/      # OpenAPI 生成 client/types
  lib/auth/               # session/BFF
```

## 修复优先级

### P0

- 移除 production demo-pay UI；修正产品和安全虚假声明。
- 在 schema/payment P0 修复前禁用真实购买入口。

### P1

- 统一 API contract；同源安全 session；应用 layout；文档/证据/case 主链路。
- 增加 root CI、前端 build/typecheck/e2e、错误监控。
- 将所有价格、状态与能力开关改为服务端真源。

### P2

- 组件化 design system、server state/cache、可访问性、SEO、性能预算。
- 建立平台 Admin 和租户设置前端。

### P3

- i18n、细节动效、更多端和浏览器插件；只有在实际发布产物存在后才展示 available。
