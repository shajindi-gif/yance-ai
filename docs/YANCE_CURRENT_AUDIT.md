# Yance 网站现状审计（Phase 0）

审计日期：2026-11-18。只读仓库与前端源码，未连接生产数据库，未改政策数据。

## 1. Git 与受保护范围

- 审计时分支：`feat/collector-yield-20261117`（`0cb2b65`）。
- 改造分支：`design/website-enterprise-20261118`，从上述提交拉出。
- 工作区已有、且本次禁止纳入提交的未提交改动：
  - `yance-ai/app/core/config.py`
  - `yance-ai/app/services/policy_collection/` 下 adapters、backfill、catalog、ops、runner、service
  - 未跟踪：`yance-ai/config/policy_sources/candidates/`、`yance-ai/scripts/policy_collection/expand_sources.py`
- 这些文件属于政策采集。本次不修改、不暂存、不覆盖。

受保护、本次不改：

- `yance-ai/` 后端、FastAPI、Agent、RAG、匹配规则、Prisma/迁移、支付与认证实现
- 政策原始数据、索引与采集配置
- `.env`、生产密钥、部署配置

允许修改：`website/` 前端展示、`docs/` 本轮说明、`website/public/sitemap.xml` 的公开营销地址。

## 2. 技术栈（以仓库为准）

| 层 | 实际情况 |
| --- | --- |
| 前端 | `website/`，Next.js 16.4.3，React 19.2.8，App Router，CSS Modules，无第三方 UI 库 |
| 后端 | `yance-ai/`，FastAPI，Python，SQLAlchemy 2，PostgreSQL + pgvector |
| 前端数据 | `website/lib/api.ts` 调用既有 `/api/v1/*`。浏览器开发时由 Next 代理到本地或 `API_PROXY_TARGET` |
| 测试 | Playwright e2e（`website/e2e/`）、`website` 的 `typecheck` / `lint` / `build`；后端 pytest 不在本轮范围 |

未更换框架、组件库或重大依赖。

## 3. 已实现、可被前端诚实展示的能力

营销页（无需登录即可打开）：`/`、`/pricing`、`/about`、`/security`、`/privacy`、`/terms`、`/policy-knowledge-base`、`/policies`、`/company-match`、`/parks`、`/demo`、`/intelligence`（部分工具需登录）、`/feedback`、`/login`、`/downloads`、`/chrome-extension`、`/roadshow`。

登录后工作区（`website/lib/navigation.ts`）：

- `/dashboard` 问衍策（带来源的提问）
- `/discover` 已发布政策目录检索，可按企业启动资格扫描
- `/opportunities` 政策机会与逐条资格
- `/applications` 申报项目、补证、材料版本
- `/companies` 企业档案与画像版本
- `/documents`、`/reports`、`/orders`、`/billing`、`/team`、`/settings`
- `/consultant`、`/tasks`、`/agents`、`/notifications`、`/projects`

定价：`/pricing` 从 `GET /api/v1/products` 读取目录，失败时显示“当前无法读取价格”。购买走既有 `/checkout`，本轮不改价格、权限和订单逻辑。

联系渠道：页脚与定价页已使用 `mailto:yanceai@163.com`。企业演示只接到这个已存在邮箱，不新增无后端的预约表单。

登录回跳：多个工作区页面使用 `/login?next=`。`/discover` 在审计时未登录会跳到 `/login` 且不带回跳，本轮只修这个前端跳转。

## 4. 政策数据：前端可以说什么

`/policy-knowledge-base` 已写明：政策数量、覆盖城市、更新频率、结构化率必须由数据库计算，当前不展示占位数字。

因此首页与行业页：

- 可以按产品枚举说明层级（国家 / 省 / 市 / 区）和支持类型字段（资助、税收、人才等）
- 可以说明用户能在已收录目录里按城市等字段筛选
- 不可以写政策条数、城市个数、高新区覆盖率、匹配成功率或补贴金额承诺

企业标签（高企、专精特新等）只作为核对主题，不表示已经认定。

## 5. 尚未作为独立产品交付的需求

以下保持为未来需求，页面上标明，不做成可点击的假结果：

- 投资组合批量政策扫描
- 城市或园区政策环境评分与横向对比报告
- 自动申报或政府认定
- 公开客户案例与成功率（现有首页已声明暂无获授权案例）

## 6. 现有视觉与信息架构

- 设计令牌在 `website/app/globals.css` 与 `website/app/design-system.css`：纸色、墨色、青色强调，无大面积渐变。
- 首页 `website/app/page.tsx` 已是证据工作台叙事，并有 Playwright 约束文案（见第 7 节）。
- 主导航是扁平链接。行业方案此前都指向同一个 `/company-match`，信息架构分不清行业。
- 全局组件：`Header`、`Footer`、`SiteChrome`、`ProductOverview`、工作区 `AppShell`。

## 7. 不能被改坏的前端契约

`website/e2e/frontend-redesign.spec.ts` 与 `audience-feedback.spec.ts` 要求首页：

- 一级标题包含“看清每项条件的依据”
- 产品图 alt 匹配“隔离合成项目的真实资格矩阵”
- `#for-business` 保留三个标题：新质生产力企业、科技与研发型企业、各类有政策需求的企业
- `#scenarios` 有 3 个场景，并写明不是真实客户案例
- `#customer-feedback` 写明案例须授权后公开
- 存在“分享使用反馈 ↗”和 FAQ“适合哪些企业”
- 移动菜单最后一项为“免费开始”，并支持 Esc 关闭

定价页标题“按次购买，需要时再买”被 `audit-journey.spec.ts` 使用，本轮不改该标题。

## 8. 本轮可安全实现的前端项

- 首页价值主张、覆盖说明（无虚构数量）、能力状态、行业入口、地域探索卡片
- 真实路由的行业方案页
- 导航与页脚链接、公开 sitemap
- `/discover` 在已加载政策上的城市与支持类型筛选，以及登录回跳

不在本轮改匹配算法、扫描请求体、支付或政策数据。
